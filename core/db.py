"""Banco de dados SQLite3 do Sistema de Análise de Vagas.

Substitui o Supabase/PostgreSQL do projeto original. Tudo fica em um único
arquivo (`vagas.db`), sem servidor e sem dependências externas.
"""
import os
import sqlite3

DB_PADRAO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vagas.db"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    salt        TEXT NOT NULL,
    criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vaga (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte            TEXT,
    id_externo       TEXT,
    titulo           TEXT NOT NULL,
    empresa          TEXT NOT NULL,
    cidade           TEXT,
    estado           TEXT,
    localizacao      TEXT,
    pais             TEXT,
    modalidade       TEXT NOT NULL DEFAULT 'nao_informado',
    senioridade      TEXT NOT NULL DEFAULT 'nao_informado',
    salario_min      REAL CHECK (salario_min IS NULL OR salario_min >= 0),
    salario_max      REAL CHECK (salario_max IS NULL OR salario_max >= 0),
    moeda            TEXT,
    salario_estimado INTEGER NOT NULL DEFAULT 0,
    descricao        TEXT,
    url_original     TEXT UNIQUE,
    url_normalizada  TEXT,
    data_publicacao  TEXT,
    data_coleta      TEXT,
    UNIQUE (fonte, id_externo)
);

CREATE TABLE IF NOT EXISTS skill (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS vaga_skill (
    vaga_id   INTEGER NOT NULL REFERENCES vaga(id)  ON DELETE CASCADE,
    skill_id  INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    PRIMARY KEY (vaga_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_vaga_data_publicacao ON vaga (data_publicacao DESC);
CREATE INDEX IF NOT EXISTS idx_vaga_senioridade     ON vaga (senioridade);
CREATE INDEX IF NOT EXISTS idx_vaga_modalidade      ON vaga (modalidade);
CREATE INDEX IF NOT EXISTS idx_vaga_cidade          ON vaga (cidade);
CREATE INDEX IF NOT EXISTS idx_vaga_skill_skill     ON vaga_skill (skill_id);
"""


def conectar(caminho: str = DB_PADRAO) -> sqlite3.Connection:
    """Abre (e cria, se necessário) o banco e garante o schema."""
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
