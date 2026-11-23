"""Gerador de vagas fictícias para demonstração (substitui a coleta Adzuna/Jobicy)."""
import random
from datetime import date, timedelta

EMPRESAS = ["Nubank", "iFood", "Stone", "Totvs", "Zup", "Dock", "CI&T", "Locaweb",
            "Mercado Livre", "Magalu", "Itaú", "Petlove", "Hotmart", "VTEX", "Sensedia"]
CIDADES = [("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
           ("Curitiba", "PR"), ("Porto Alegre", "RS"), ("Recife", "PE"),
           ("Florianópolis", "SC"), ("Salvador", "BA"), ("Brasília", "DF")]
PERFIS = [
    ("Desenvolvedor Backend", ["Python", "PostgreSQL", "Docker", "AWS"]),
    ("Desenvolvedor Backend", ["Java", "Spring Boot", "MySQL", "Kafka"]),
    ("Desenvolvedor Frontend", ["React", "TypeScript", "JavaScript"]),
    ("Desenvolvedor Full Stack", ["Node.js", "React", "MongoDB", "JavaScript"]),
    ("Desenvolvedor Mobile", ["Flutter", "Dart"]),
    ("Desenvolvedor .NET", ["C#", ".NET", "SQL", "Azure"]),
    ("Analista de Dados", ["Python", "SQL", "Power BI", "Pandas"]),
    ("Engenheiro de Dados", ["Python", "Apache Spark", "Airflow", "Snowflake"]),
    ("Cientista de Dados", ["Python", "Machine Learning", "TensorFlow", "Pandas"]),
    ("Engenheiro DevOps", ["Kubernetes", "Terraform", "Docker", "Linux", "AWS"]),
    ("Desenvolvedor PHP", ["PHP", "MySQL", "Linux"]),
    ("Desenvolvedor Golang", ["Golang", "Redis", "Kubernetes"]),
]
NIVEIS = {"estagio": (1500, 2800), "junior": (3000, 6000), "pleno": (6500, 11000),
          "senior": (11000, 20000), "trainee": (3500, 5500)}


def gerar(qtd: int = 80, semente: int = 7) -> list:
    rnd = random.Random(semente)
    hoje = date.today()
    vagas = []
    for i in range(qtd):
        titulo, skills = rnd.choice(PERFIS)
        nivel = rnd.choices(list(NIVEIS), weights=[1, 1, 4, 4, 2, ][:5])[0]
        cidade, uf = rnd.choice(CIDADES)
        lo, hi = NIVEIS[nivel]
        base = rnd.randint(lo, hi - 500)
        tem_salario = rnd.random() < 0.75
        nome_nivel = {"estagio": "Estagiário", "junior": "Júnior", "pleno": "Pleno",
                      "senior": "Sênior", "trainee": "Trainee"}[nivel]
        vagas.append({
            "fonte": "exemplo", "id_externo": f"EX-{semente}-{i:04d}",
            "titulo": f"{titulo} {nome_nivel}",
            "empresa": rnd.choice(EMPRESAS),
            "cidade": cidade, "estado": uf, "localizacao": f"{cidade}, {uf}",
            "modalidade": rnd.choice(["remoto", "remoto", "hibrido", "presencial"]),
            "senioridade": nivel,
            "salario_min": base if tem_salario else None,
            "salario_max": base + rnd.randint(500, 3000) if tem_salario else None,
            "moeda": "BRL",
            "descricao": f"Buscamos {titulo.lower()} com experiência em {', '.join(skills)}.",
            "url_original": f"https://exemplo.com/vagas/{semente}-{i}",
            "data_publicacao": (hoje - timedelta(days=rnd.randint(0, 150))).isoformat(),
            "skills": rnd.sample(skills, k=max(2, len(skills) - rnd.randint(0, 1))),
        })
    return vagas
