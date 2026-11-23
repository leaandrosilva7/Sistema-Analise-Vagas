"""Sincronização (somente leitura) Supabase/PostgreSQL -> SQLite local.

O ETL continua gravando no Supabase; este módulo apenas COPIA as vagas para o
vagas.db. Nada é escrito ou apagado no Supabase.
"""
import os
import re
from datetime import date, datetime

from . import formatadores as fmt

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ErroSync(Exception):
    """Falha de sincronização com mensagem pronta para o usuário."""


def ler_env(caminhos=None) -> dict:
    """Lê KEY=VALUE de .env (pasta do app e pasta atual). Variáveis do sistema têm prioridade."""
    valores = {}
    for c in caminhos or [os.path.join(RAIZ, ".env"), os.path.join(os.getcwd(), ".env")]:
        if os.path.isfile(c):
            with open(c, encoding="utf-8-sig") as f:
                for linha in f:
                    linha = linha.strip()
                    if not linha or linha.startswith("#") or "=" not in linha:
                        continue
                    k, v = linha.split("=", 1)
                    valores.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    for k in ("DATABASE_URL",):
        if os.environ.get(k):
            valores[k] = os.environ[k]
    return valores


def buscar_remoto(database_url: str):
    """Baixa vagas e skills do Supabase. Devolve (vagas: list[dict], skills: {vaga_id: [nomes]})."""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        raise ErroSync("O pacote psycopg2 não está instalado.\nRode:  pip install psycopg2-binary")
    if not database_url:
        raise ErroSync("DATABASE_URL não encontrada.\nCopie o arquivo .env do seu projeto ETL para a pasta do sistema "
                       "(ou crie um a partir de .env.example).")
    try:
        conn = psycopg2.connect(database_url, connect_timeout=15)
    except Exception as e:  # noqa: BLE001
        msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
        raise ErroSync(f"Não foi possível conectar ao Supabase:\n{msg}")
    try:
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM vaga ORDER BY id")
        vagas = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT vs.vaga_id, s.nome FROM vaga_skill vs JOIN skill s ON s.id = vs.skill_id")
        skills = {}
        for r in cur.fetchall():
            skills.setdefault(r["vaga_id"], []).append(r["nome"])
        return vagas, skills
    except Exception as e:  # noqa: BLE001
        msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
        raise ErroSync(f"Erro ao ler os dados do Supabase:\n{msg}")
    finally:
        conn.close()


def _txt(v):
    v = None if v is None else str(v).strip()
    return v or None


def _data(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    return _txt(v)[:10] if _txt(v) else None


def _num(v):
    try:
        n = None if v is None else float(v)
    except (TypeError, ValueError):
        return None
    return n if n is not None and n >= 0 else None


def aplicar_remotos(conn, vagas: list, skills: dict) -> dict:
    """Insere/atualiza no SQLite. Casa por (fonte, id_externo) ou url_original.
    Vagas cadastradas só localmente nunca são apagadas."""
    inseridas = atualizadas = ignoradas = 0
    campos = ["fonte", "id_externo", "titulo", "empresa", "cidade", "estado", "localizacao", "pais",
              "modalidade", "senioridade", "salario_min", "salario_max", "moeda", "salario_estimado",
              "descricao", "url_original", "url_normalizada", "data_publicacao", "data_coleta"]
    for r in vagas:
        v = {
            "fonte": _txt(r.get("fonte")), "id_externo": _txt(r.get("id_externo")),
            "titulo": _txt(r.get("titulo")), "empresa": _txt(r.get("empresa")),
            "cidade": _txt(r.get("cidade")), "estado": _txt(r.get("estado")),
            "localizacao": _txt(r.get("localizacao")), "pais": _txt(r.get("pais")),
            "modalidade": fmt.normalizar_modalidade(r.get("modalidade")),
            "senioridade": fmt.normalizar_senioridade(r.get("senioridade")),
            "salario_min": _num(r.get("salario_min")), "salario_max": _num(r.get("salario_max")),
            "moeda": (_txt(r.get("moeda")) or "BRL").upper(),
            "salario_estimado": 1 if r.get("salario_estimado") else 0,
            "descricao": _txt(r.get("descricao")), "url_original": _txt(r.get("url_original")),
            "url_normalizada": _txt(r.get("url_normalizada")),
            "data_publicacao": _data(r.get("data_publicacao")), "data_coleta": _data(r.get("data_coleta")),
        }
        if not v["titulo"] or not v["empresa"] or not (v["url_original"] or (v["fonte"] and v["id_externo"])):
            ignoradas += 1
            continue
        if v["salario_min"] is not None and v["salario_max"] is not None and v["salario_min"] > v["salario_max"]:
            v["salario_min"], v["salario_max"] = v["salario_max"], v["salario_min"]

        existente = None
        if v["fonte"] and v["id_externo"]:
            existente = conn.execute("SELECT id FROM vaga WHERE fonte=? AND id_externo=?",
                                     (v["fonte"], v["id_externo"])).fetchone()
        if not existente and v["url_original"]:
            existente = conn.execute("SELECT id FROM vaga WHERE url_original=?", (v["url_original"],)).fetchone()
        try:
            if existente:
                vid = existente["id"]
                conn.execute(f"UPDATE vaga SET {', '.join(c + '=?' for c in campos)} WHERE id=?",
                             [v[c] for c in campos] + [vid])
                atualizadas += 1
            else:
                cur = conn.execute(f"INSERT INTO vaga ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})",
                                   [v[c] for c in campos])
                vid = cur.lastrowid
                inseridas += 1
        except Exception:  # noqa: BLE001  (conflito de URL etc.: não derruba a sincronização)
            ignoradas += 1
            continue

        nomes = list(dict.fromkeys(n.strip() for n in skills.get(r.get("id"), []) if n and n.strip()))
        if nomes:
            conn.execute("DELETE FROM vaga_skill WHERE vaga_id=?", (vid,))
            for n in nomes:
                conn.execute("INSERT OR IGNORE INTO skill (nome) VALUES (?)", (n,))
                sid = conn.execute("SELECT id FROM skill WHERE nome=?", (n,)).fetchone()[0]
                conn.execute("INSERT OR IGNORE INTO vaga_skill (vaga_id, skill_id) VALUES (?,?)", (vid, sid))
        elif not existente:
            from .salary_stats import detectar_tecnologias
            for n in detectar_tecnologias(f"{v['titulo']} {v['descricao'] or ''}"):
                conn.execute("INSERT OR IGNORE INTO skill (nome) VALUES (?)", (n,))
                sid = conn.execute("SELECT id FROM skill WHERE nome=?", (n,)).fetchone()[0]
                conn.execute("INSERT OR IGNORE INTO vaga_skill (vaga_id, skill_id) VALUES (?,?)", (vid, sid))
    conn.commit()
    return {"recebidas": len(vagas), "inseridas": inseridas, "atualizadas": atualizadas, "ignoradas": ignoradas}
