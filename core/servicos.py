"""Regras de negócio: autenticação, CRUD de vagas, dashboard, relatórios e importação.

Reúne o que no projeto original estava em authController, vagasController,
dashboardController e coletaController.
"""
import csv
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import date, timedelta

from . import formatadores as fmt
from .salary_stats import calcular_estatisticas_salariais, detectar_tecnologias, obter_tecnologias

CAMPOS_VAGA = [
    "fonte", "id_externo", "titulo", "empresa", "cidade", "estado", "localizacao", "pais",
    "modalidade", "senioridade", "salario_min", "salario_max", "moeda", "salario_estimado",
    "descricao", "url_original", "url_normalizada", "data_publicacao", "data_coleta",
]
LIMITE_COMPARACAO = 10
LIMITE_IMPORTACAO = 5000


ErroValidacao = fmt.ErroValidacao


# ----------------------------------------------------------------- Autenticação
def _hash_senha(senha: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 200_000).hex()


class Servico:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ---- usuários (UC01, UC02) ------------------------------------------------
    def registrar(self, email: str, senha: str, nome: str = "") -> dict:
        email = (email or "").strip().lower()
        if not email or not senha:
            raise ErroValidacao("Email e senha são obrigatórios.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ErroValidacao("Informe um email válido.")
        if len(senha) < 6:
            raise ErroValidacao("A senha deve ter pelo menos 6 caracteres.")
        salt = secrets.token_bytes(16)
        try:
            cur = self.conn.execute(
                "INSERT INTO usuario (nome, email, senha_hash, salt) VALUES (?,?,?,?)",
                ((nome or "").strip(), email, _hash_senha(senha, salt), salt.hex()),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ErroValidacao("Este email já está cadastrado.")
        return {"id": cur.lastrowid, "nome": (nome or "").strip(), "email": email}

    def login(self, email: str, senha: str) -> dict:
        email = (email or "").strip().lower()
        if not email or not senha:
            raise ErroValidacao("Email e senha são obrigatórios.")
        row = self.conn.execute("SELECT * FROM usuario WHERE email = ?", (email,)).fetchone()
        if not row:
            raise ErroValidacao("Email ou senha inválidos.")
        esperado = _hash_senha(senha, bytes.fromhex(row["salt"]))
        if not hmac.compare_digest(esperado, row["senha_hash"]):
            raise ErroValidacao("Email ou senha inválidos.")
        return {"id": row["id"], "nome": row["nome"], "email": row["email"]}

    def total_usuarios(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM usuario").fetchone()[0]

    # ---- helpers de vaga -------------------------------------------------------
    def _skills_da_vaga(self, vaga_id: int) -> list:
        rows = self.conn.execute(
            "SELECT s.nome FROM skill s JOIN vaga_skill vs ON vs.skill_id = s.id "
            "WHERE vs.vaga_id = ? ORDER BY s.nome COLLATE NOCASE",
            (vaga_id,),
        ).fetchall()
        return [r["nome"] for r in rows]

    def _gravar_skills(self, vaga_id: int, skills) -> None:
        self.conn.execute("DELETE FROM vaga_skill WHERE vaga_id = ?", (vaga_id,))
        for nome in dict.fromkeys(s.strip() for s in skills if s and s.strip()):
            self.conn.execute("INSERT OR IGNORE INTO skill (nome) VALUES (?)", (nome,))
            sid = self.conn.execute("SELECT id FROM skill WHERE nome = ?", (nome,)).fetchone()[0]
            self.conn.execute(
                "INSERT OR IGNORE INTO vaga_skill (vaga_id, skill_id) VALUES (?,?)", (vaga_id, sid)
            )

    def _para_dict(self, row) -> dict:
        d = dict(row)
        d["skills"] = self._skills_da_vaga(d["id"])
        return d

    @staticmethod
    def _limpar(dados: dict) -> dict:
        """Valida e normaliza os campos de uma vaga (entrada do formulário ou importação)."""
        txt = lambda k: (str(dados.get(k) or "").strip() or None)  # noqa: E731
        v = {
            "fonte": txt("fonte"),
            "id_externo": txt("id_externo"),
            "titulo": txt("titulo"),
            "empresa": txt("empresa"),
            "cidade": txt("cidade"),
            "estado": txt("estado"),
            "localizacao": txt("localizacao"),
            "pais": txt("pais"),
            "descricao": txt("descricao"),
            "url_original": txt("url_original"),
            "url_normalizada": txt("url_normalizada"),
            "modalidade": fmt.normalizar_modalidade(dados.get("modalidade")),
            "senioridade": fmt.normalizar_senioridade(dados.get("senioridade")),
            "moeda": (txt("moeda") or "BRL").upper(),
            "salario_estimado": 1 if str(dados.get("salario_estimado")).lower() in ("1", "true", "sim") else 0,
        }
        if not v["titulo"]:
            raise ErroValidacao("O título é obrigatório.")
        if not v["empresa"]:
            raise ErroValidacao("A empresa é obrigatória.")
        if v["url_original"] and not re.match(r"^https?://", v["url_original"], re.I):
            raise ErroValidacao("O link original deve começar com http:// ou https://.")

        for campo in ("salario_min", "salario_max"):
            valor = dados.get(campo)
            if isinstance(valor, str) or valor is None:
                valor = fmt.parse_numero(valor)
            if valor is not None and (float(valor) < 0):
                raise ErroValidacao(f"O campo {campo.replace('_', ' ')} não pode ser negativo.")
            v[campo] = None if valor is None else float(valor)
        if v["salario_min"] is not None and v["salario_max"] is not None and v["salario_min"] > v["salario_max"]:
            raise ErroValidacao("O salário mínimo não pode ser maior que o máximo.")

        v["data_publicacao"] = fmt.parse_data(dados.get("data_publicacao"))
        v["data_coleta"] = fmt.parse_data(dados.get("data_coleta")) or fmt.hoje()
        return v

    @staticmethod
    def _lista_skills(skills) -> list:
        if isinstance(skills, str):
            skills = re.split(r"[,;|]", skills)
        return [s.strip() for s in (skills or []) if s and s.strip()]

    # ---- CRUD de vagas ---------------------------------------------------------
    def criar_vaga(self, dados: dict, skills=None) -> int:
        """INCLUSÃO. Sem skills informadas, detecta pelo título/descrição."""
        v = self._limpar(dados)
        lista = self._lista_skills(skills) or detectar_tecnologias(f"{v['titulo']} {v['descricao'] or ''}")
        cols = ", ".join(CAMPOS_VAGA)
        marcas = ", ".join("?" for _ in CAMPOS_VAGA)
        try:
            cur = self.conn.execute(
                f"INSERT INTO vaga ({cols}) VALUES ({marcas})", [v.get(c) for c in CAMPOS_VAGA]
            )
            self._gravar_skills(cur.lastrowid, lista)
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise ErroValidacao("Já existe uma vaga com este link original ou identificador da fonte.")
        return cur.lastrowid

    def obter_vaga(self, vaga_id: int) -> dict:
        """CONSULTA de uma vaga."""
        row = self.conn.execute("SELECT * FROM vaga WHERE id = ?", (vaga_id,)).fetchone()
        if not row:
            raise ErroValidacao("Vaga não encontrada.")
        return self._para_dict(row)

    def detalhes_vaga(self, vaga_id: int) -> dict:
        """Vaga + estatística salarial relacionada (mesma senioridade e 1ª tecnologia)."""
        vaga = self.obter_vaga(vaga_id)
        techs = obter_tecnologias(vaga)
        estat = calcular_estatisticas_salariais(
            self._vagas_com_salario(),
            senioridade=vaga["senioridade"] if vaga["senioridade"] != "nao_informado" else None,
            tecnologia=techs[0] if techs else None,
        )
        return {"vaga": vaga, "estatistica_salarial_relacionada": estat}

    def atualizar_vaga(self, vaga_id: int, dados: dict, skills=None) -> None:
        """ALTERAÇÃO."""
        self.obter_vaga(vaga_id)
        v = self._limpar(dados)
        sets = ", ".join(f"{c} = ?" for c in CAMPOS_VAGA)
        lista = self._lista_skills(skills) or detectar_tecnologias(f"{v['titulo']} {v['descricao'] or ''}")
        try:
            self.conn.execute(
                f"UPDATE vaga SET {sets} WHERE id = ?", [v.get(c) for c in CAMPOS_VAGA] + [vaga_id]
            )
            self._gravar_skills(vaga_id, lista)
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise ErroValidacao("Já existe outra vaga com este link original ou identificador da fonte.")

    def excluir_vaga(self, vaga_id: int) -> None:
        """REMOÇÃO."""
        cur = self.conn.execute("DELETE FROM vaga WHERE id = ?", (vaga_id,))
        self.conn.commit()
        if cur.rowcount == 0:
            raise ErroValidacao("Vaga não encontrada.")

    def excluir_vagas(self, ids) -> int:
        ids = [int(i) for i in ids]
        if not ids:
            return 0
        cur = self.conn.execute(
            f"DELETE FROM vaga WHERE id IN ({','.join('?' * len(ids))})", ids
        )
        self.conn.commit()
        return cur.rowcount

    def listar_vagas(self, filtros: dict = None, pagina: int = 1, limite: int = 30):
        """CONSULTA com filtros (UC03, UC04, UC09-UC14). Devolve (vagas, total)."""
        f = filtros or {}
        if pagina < 1 or not 1 <= limite <= 500:
            raise ErroValidacao("Paginação inválida.")
        where, params = [], []

        if (f.get("texto") or "").strip():
            like = f"%{f['texto'].strip()}%"
            where.append("(v.titulo LIKE ? OR v.empresa LIKE ? OR v.descricao LIKE ?)")
            params += [like, like, like]
        if (f.get("cidade") or "").strip():
            like = f"%{f['cidade'].strip()}%"
            where.append("(v.cidade LIKE ? OR v.estado LIKE ? OR v.localizacao LIKE ?)")
            params += [like, like, like]
        if f.get("senioridade"):
            where.append("v.senioridade = ?")
            params.append(fmt.normalizar_senioridade(f["senioridade"]))
        if f.get("modalidade"):
            where.append("v.modalidade = ?")
            params.append(fmt.normalizar_modalidade(f["modalidade"]))
        if (f.get("tecnologia") or "").strip():
            where.append(
                "v.id IN (SELECT vs.vaga_id FROM vaga_skill vs JOIN skill s ON s.id = vs.skill_id "
                "WHERE s.nome LIKE ?)"
            )
            params.append(f"%{f['tecnologia'].strip()}%")
        if f.get("periodo"):
            dias = int(f["periodo"])
            if not 1 <= dias <= 3650:
                raise ErroValidacao("O período deve estar entre 1 e 3650 dias.")
            where.append("v.data_publicacao >= ?")
            params.append((date.today() - timedelta(days=dias)).isoformat())

        sql_where = (" WHERE " + " AND ".join(where)) if where else ""
        total = self.conn.execute(f"SELECT COUNT(*) FROM vaga v{sql_where}", params).fetchone()[0]
        rows = self.conn.execute(
            f"SELECT v.* FROM vaga v{sql_where} "
            "ORDER BY v.data_publicacao DESC, v.id DESC LIMIT ? OFFSET ?",
            params + [limite, (pagina - 1) * limite],
        ).fetchall()
        return [self._para_dict(r) for r in rows], total

    def vagas_recentes(self, n: int = 10) -> list:
        rows = self.conn.execute(
            "SELECT * FROM vaga ORDER BY data_publicacao DESC, id DESC LIMIT ?", (n,)
        ).fetchall()
        return [self._para_dict(r) for r in rows]

    def comparar_vagas(self, ids) -> list:
        ids = list(dict.fromkeys(int(i) for i in ids))
        if len(ids) < 2:
            raise ErroValidacao("Selecione pelo menos duas vagas para comparar.")
        if len(ids) > LIMITE_COMPARACAO:
            raise ErroValidacao(f"A comparação permite no máximo {LIMITE_COMPARACAO} vagas.")
        rows = self.conn.execute(
            f"SELECT * FROM vaga WHERE id IN ({','.join('?' * len(ids))})", ids
        ).fetchall()
        por_id = {r["id"]: self._para_dict(r) for r in rows}
        return [por_id[i] for i in ids if i in por_id]

    def total_vagas(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM vaga").fetchone()[0]

    # ---- Dashboard (UC05-UC08, UC17, UC18) ------------------------------------
    def _vagas_com_salario(self, dias: int = None) -> list:
        sql = "SELECT * FROM vaga WHERE (salario_min IS NOT NULL OR salario_max IS NOT NULL)"
        params = []
        if dias:
            sql += " AND data_publicacao >= ?"
            params.append((date.today() - timedelta(days=dias)).isoformat())
        return [self._para_dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def metricas(self) -> dict:
        total = self.total_vagas()
        remotas = self.conn.execute("SELECT COUNT(*) FROM vaga WHERE modalidade = 'remoto'").fetchone()[0]
        # Média por vaga (e não por tecnologia) para não contar a mesma vaga duas vezes.
        pontos = []
        for v in self._vagas_com_salario():
            if (v["moeda"] or "").upper() != "BRL":
                continue
            mn, mx = v["salario_min"], v["salario_max"]
            ok = lambda x: x is not None and 500 <= x <= 200000  # noqa: E731
            if not ok(mn) and not ok(mx):
                continue
            if ok(mn) and ok(mx) and mn > mx:
                continue
            pontos.append((mn + mx) / 2 if ok(mn) and ok(mx) else (mn if ok(mn) else mx))
        top = self.conn.execute(
            "SELECT s.nome, COUNT(*) c FROM skill s JOIN vaga_skill vs ON vs.skill_id = s.id "
            "GROUP BY s.id ORDER BY c DESC, s.nome LIMIT 1"
        ).fetchone()
        return {
            "total_vagas": total,
            "salario_medio": round(sum(pontos) / len(pontos), 2) if pontos else 0,
            "percentual_remoto": round(100 * remotas / total, 1) if total else 0,
            "skill_top": top["nome"] if top else "N/A",
            "vagas_com_salario": len(pontos),
        }

    def tecnologias_demandadas(self, periodo: str = None) -> list:
        """[{'tecnologia','periodo'(AAAA-MM),'total_vagas'}] ordenado por período e total."""
        sql = (
            "SELECT s.nome AS tecnologia, substr(v.data_publicacao,1,7) AS periodo, COUNT(*) AS total_vagas "
            "FROM vaga v JOIN vaga_skill vs ON vs.vaga_id = v.id JOIN skill s ON s.id = vs.skill_id "
            "WHERE v.data_publicacao IS NOT NULL"
        )
        params = []
        if periodo:
            sql += " AND substr(v.data_publicacao,1,7) = ?"
            params.append(periodo)
        sql += " GROUP BY s.id, periodo ORDER BY periodo ASC, total_vagas DESC, s.nome"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def tendencias(self) -> list:
        rows = self.conn.execute(
            "SELECT substr(data_publicacao,1,7) AS periodo, COUNT(*) AS total_vagas FROM vaga "
            "WHERE data_publicacao IS NOT NULL GROUP BY periodo ORDER BY periodo"
        ).fetchall()
        return [dict(r) for r in rows]

    def estatisticas_salariais(self, tecnologia=None, senioridade=None, periodo=365) -> list:
        if periodo is not None and not 1 <= int(periodo) <= 3650:
            raise ErroValidacao("O período deve estar entre 1 e 3650 dias.")
        return calcular_estatisticas_salariais(
            self._vagas_com_salario(int(periodo) if periodo else None),
            senioridade=senioridade or None,
            tecnologia=tecnologia or None,
        )

    # ---- Relatório de informações ----------------------------------------------
    def relatorio(self) -> dict:
        q = lambda sql: [tuple(r) for r in self.conn.execute(sql).fetchall()]  # noqa: E731
        m = self.metricas()
        return {
            "gerado_em": fmt.hoje(),
            "total_vagas": m["total_vagas"],
            "salario_medio": m["salario_medio"],
            "percentual_remoto": m["percentual_remoto"],
            "total_empresas": self.conn.execute("SELECT COUNT(DISTINCT empresa) FROM vaga").fetchone()[0],
            "por_senioridade": q("SELECT senioridade, COUNT(*) FROM vaga GROUP BY 1 ORDER BY 2 DESC"),
            "por_modalidade": q("SELECT modalidade, COUNT(*) FROM vaga GROUP BY 1 ORDER BY 2 DESC"),
            "por_estado": q(
                "SELECT COALESCE(NULLIF(estado,''),'Não informado'), COUNT(*) FROM vaga "
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
            ),
            "top_empresas": q("SELECT empresa, COUNT(*) FROM vaga GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 10"),
            "top_tecnologias": q(
                "SELECT s.nome, COUNT(*) FROM skill s JOIN vaga_skill vs ON vs.skill_id = s.id "
                "GROUP BY s.id ORDER BY 2 DESC, 1 LIMIT 10"
            ),
            "salarios": self.estatisticas_salariais(periodo=None),
        }

    def relatorio_texto(self) -> str:
        r = self.relatorio()
        L = []
        add = L.append
        add("RELATÓRIO DE VAGAS DE TECNOLOGIA")
        add(f"Gerado em {fmt.formatar_data(r['gerado_em'])}")
        add("=" * 60)
        add(f"Total de vagas ........ {r['total_vagas']}")
        add(f"Empresas distintas .... {r['total_empresas']}")
        add(f"Salário médio ......... {fmt.formatar_moeda(r['salario_medio']) if r['salario_medio'] else 'Não informado'}")
        add(f"Trabalho remoto ....... {r['percentual_remoto']}%")

        def bloco(titulo, linhas, rotulo=lambda x: x):
            add("")
            add(titulo)
            add("-" * 60)
            if not linhas:
                add("  (sem dados)")
            for nome, qtd in linhas:
                add(f"  {str(rotulo(nome)):<40} {qtd:>6}")

        bloco("Vagas por senioridade", r["por_senioridade"], fmt.formatar_senioridade)
        bloco("Vagas por modalidade", r["por_modalidade"], fmt.formatar_modalidade)
        bloco("Vagas por estado (top 10)", r["por_estado"])
        bloco("Empresas que mais contratam (top 10)", r["top_empresas"])
        bloco("Tecnologias mais citadas (top 10)", r["top_tecnologias"])
        add("")
        add("Estatísticas salariais (BRL) por tecnologia e senioridade")
        add("-" * 60)
        if not r["salarios"]:
            add("  (sem dados)")
        for s in r["salarios"]:
            add(
                f"  {s['tecnologia']:<18} {fmt.formatar_senioridade(s['senioridade']):<10} "
                f"média {fmt.formatar_moeda(s['salario_medio']):>14}  ({s['total_vagas']} vagas)"
            )
        return "\n".join(L)

    # ---- Importação (coleta) ---------------------------------------------------
    def importar_vagas(self, registros: list) -> dict:
        """Equivalente a POST /coleta/vagas: valida, deduplica e insere. Nunca duplica."""
        if not registros:
            raise ErroValidacao("O arquivo não contém vagas.")
        if len(registros) > LIMITE_IMPORTACAO:
            raise ErroValidacao(f"Importe no máximo {LIMITE_IMPORTACAO} vagas por vez.")
        inseridas = duplicadas = 0
        rejeitadas = []
        for i, reg in enumerate(registros, start=1):
            try:
                if not isinstance(reg, dict):
                    raise ErroValidacao("registro inválido")
                if not reg.get("url_original") and not (reg.get("fonte") and reg.get("id_externo")):
                    raise ErroValidacao("informe link original ou fonte + id_externo")
                v = self._limpar(reg)
                existe = False
                if v["url_original"]:
                    existe = self.conn.execute(
                        "SELECT 1 FROM vaga WHERE url_original = ?", (v["url_original"],)
                    ).fetchone()
                if not existe and v["fonte"] and v["id_externo"]:
                    existe = self.conn.execute(
                        "SELECT 1 FROM vaga WHERE fonte = ? AND id_externo = ?", (v["fonte"], v["id_externo"])
                    ).fetchone()
                if existe:
                    duplicadas += 1
                    continue
                self.criar_vaga(reg, reg.get("skills"))
                inseridas += 1
            except ErroValidacao as e:
                rejeitadas.append(f"linha {i}: {e}")
        return {
            "total_recebido": len(registros),
            "inseridas": inseridas,
            "duplicadas": duplicadas,
            "rejeitadas": len(rejeitadas),
            "erros": rejeitadas[:20],
        }

    def importar_arquivo(self, caminho: str) -> dict:
        ext = os.path.splitext(caminho)[1].lower()
        if ext == ".json":
            with open(caminho, encoding="utf-8-sig") as f:
                dados = json.load(f)
            if isinstance(dados, dict):
                dados = dados.get("vagas", [])
        elif ext == ".csv":
            with open(caminho, encoding="utf-8-sig", newline="") as f:
                amostra = f.read(4096)
                f.seek(0)
                try:
                    dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
                except csv.Error:
                    dialeto = csv.excel
                dados = list(csv.DictReader(f, dialect=dialeto))
        else:
            raise ErroValidacao("Formato não suportado. Use .csv ou .json.")
        return self.importar_vagas(dados)


# ----------------------------------------------------------------- Exportação CSV
def _celula_segura(valor) -> str:
    """Evita injeção de fórmulas ao abrir o CSV no Excel (igual a exportCsv.js)."""
    texto = "" if valor is None else str(valor)
    if re.match(r"^\s*[=+\-@]", texto):
        texto = "'" + texto
    return texto


def exportar_csv(caminho: str, cabecalho: list, linhas: list) -> None:
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow([_celula_segura(c) for c in cabecalho])
        for linha in linhas:
            w.writerow([_celula_segura(c) for c in linha])
