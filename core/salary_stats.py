"""Estatísticas salariais (porta de backend/src/services/salaryStats.js)."""
import re

from .formatadores import normalizar_senioridade, sem_acento

TECNOLOGIAS = [
    "JavaScript", "TypeScript", "React Native", "Node.js", "Next.js",
    "Spring Boot", "Machine Learning", "Power BI", "PostgreSQL", "MongoDB",
    "Kubernetes", "TensorFlow", "GitHub Actions", "Apache Spark", "Snowflake",
    "Python", "React", "Angular", "Vue", "Java", "SQL", "AWS", "Azure",
    "Docker", "Airflow", "Spark", "Kafka", "Redis", "MySQL", "Golang",
    "Flutter", "C#", "C++", ".NET", "PHP", "Ruby", "Rust", "Scala",
    "Terraform", "Pandas", "Tableau", "BigQuery", "Hadoop", "dbt", "Linux",
]

_PADROES = {
    t: re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)", re.IGNORECASE)
    for t in TECNOLOGIAS
}

SALARIO_MIN_VALIDO = 500
SALARIO_MAX_VALIDO = 200000


def detectar_tecnologias(texto: str) -> list:
    """Procura tecnologias conhecidas dentro de um texto livre."""
    return [t for t, padrao in _PADROES.items() if padrao.search(texto or "")]


def obter_tecnologias(vaga: dict) -> list:
    """Skills cadastradas; se não houver, detecta pelo título/descrição."""
    skills = [s for s in (vaga.get("skills") or []) if s]
    if skills:
        return list(dict.fromkeys(skills))
    return detectar_tecnologias(f"{vaga.get('titulo') or ''} {vaga.get('descricao') or ''}")


def _valido(v) -> bool:
    return v is not None and SALARIO_MIN_VALIDO <= v <= SALARIO_MAX_VALIDO


def _media(valores):
    return round(sum(valores) / len(valores), 2) if valores else None


def calcular_estatisticas_salariais(vagas, senioridade=None, tecnologia=None) -> list:
    """Agrupa por (tecnologia, senioridade) e devolve médias de mín/máx/ponto médio.

    Considera apenas vagas em BRL com faixa plausível (R$ 500 a R$ 200.000).
    """
    grupos = {}
    nivel_filtro = normalizar_senioridade(senioridade) if senioridade else None

    for vaga in vagas or []:
        nivel = normalizar_senioridade(vaga.get("senioridade"))
        if nivel_filtro and nivel != nivel_filtro:
            continue
        if (vaga.get("moeda") or "").upper() != "BRL":
            continue

        mn, mx = vaga.get("salario_min"), vaga.get("salario_max")
        ok_min, ok_max = _valido(mn), _valido(mx)
        if not ok_min and not ok_max:
            continue
        if ok_min and ok_max and mn > mx:
            continue

        skills = obter_tecnologias(vaga)
        if tecnologia:
            skills = [s for s in skills if s.lower() == tecnologia.lower()]
            if not skills:
                continue
        lista = skills or ["Não informada"]

        for skill in lista:
            g = grupos.setdefault(
                (skill, nivel),
                {"tecnologia": skill, "senioridade": nivel, "mins": [], "maxs": [], "pontos": []},
            )
            if ok_min:
                g["mins"].append(mn)
            if ok_max:
                g["maxs"].append(mx)
            g["pontos"].append((mn + mx) / 2 if ok_min and ok_max else (mn if ok_min else mx))

    resultado = [
        {
            "tecnologia": g["tecnologia"],
            "senioridade": g["senioridade"],
            "salario_min_medio": _media(g["mins"]),
            "salario_max_medio": _media(g["maxs"]),
            "salario_medio": _media(g["pontos"]),
            "total_vagas": len(g["pontos"]),
        }
        for g in grupos.values()
    ]
    resultado.sort(key=lambda r: (sem_acento(r["tecnologia"]).lower(), r["senioridade"]))
    return resultado
