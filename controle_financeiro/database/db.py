import os
import sqlite3
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover - ambiente local sem dependencia opcional
    psycopg = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "database.db"


def obter_configuracao(chave, default=None):
    valor = os.getenv(chave)

    if valor:
        return valor

    try:
        import streamlit as st

        return st.secrets.get(chave, default)
    except Exception:
        return default


def obter_database_url():
    return obter_configuracao("DATABASE_URL")


def usa_postgres():
    database_url = obter_database_url()
    return bool(database_url and database_url.startswith(("postgres://", "postgresql://")))


def descrever_backend():
    if usa_postgres():
        return "PostgreSQL externo"

    return "SQLite local"


def conectar():
    database_url = obter_database_url()

    if database_url:
        if psycopg is None:
            raise RuntimeError(
                "DATABASE_URL configurado, mas a dependencia 'psycopg' nao esta instalada."
            )

        return psycopg.connect(database_url)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def e_postgres(conn):
    return conn.__class__.__module__.startswith("psycopg")


def adaptar_placeholders(sql, conn):
    if e_postgres(conn):
        return sql.replace("?", "%s")

    return sql


def executar(conn, cursor, sql, params=None):
    params = params or ()
    cursor.execute(adaptar_placeholders(sql, conn), params)


def buscar_colunas_tabela(conn, tabela):
    cursor = conn.cursor()

    if e_postgres(conn):
        executar(
            conn,
            cursor,
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = ?
            """,
            (tabela,),
        )
        return {linha[0] for linha in cursor.fetchall()}

    executar(conn, cursor, f"PRAGMA table_info({tabela})")
    return {coluna[1] for coluna in cursor.fetchall()}
