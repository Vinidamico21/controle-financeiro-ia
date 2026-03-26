from datetime import datetime, timezone
import json

from database.db import conectar, executar
from database.models import criar_tabela


def _abrir_conexao(conn=None):
    if conn is not None:
        return conn, False

    nova_conn = conectar()
    criar_tabela(nova_conn)
    return nova_conn, True


def salvar_artefato(chave, payload, metadata=None, conn=None):
    conn, criada_internamente = _abrir_conexao(conn)
    cursor = conn.cursor()
    metadata_serializada = json.dumps(metadata or {}, ensure_ascii=True)
    atualizado_em = datetime.now(timezone.utc).isoformat()

    executar(conn, cursor, "DELETE FROM artefatos_sistema WHERE chave = ?", (chave,))
    executar(
        conn,
        cursor,
        """
        INSERT INTO artefatos_sistema (chave, payload, metadata, atualizado_em)
        VALUES (?, ?, ?, ?)
        """,
        (chave, payload, metadata_serializada, atualizado_em),
    )
    conn.commit()

    if criada_internamente:
        conn.close()


def carregar_artefato(chave, conn=None):
    conn, criada_internamente = _abrir_conexao(conn)
    cursor = conn.cursor()
    executar(
        conn,
        cursor,
        """
        SELECT payload, metadata, atualizado_em
        FROM artefatos_sistema
        WHERE chave = ?
        """,
        (chave,),
    )
    linha = cursor.fetchone()

    if criada_internamente:
        conn.close()

    if not linha:
        return None

    payload, metadata, atualizado_em = linha

    if isinstance(payload, memoryview):
        payload = payload.tobytes()

    return {
        "payload": payload,
        "metadata": json.loads(metadata) if metadata else {},
        "atualizado_em": atualizado_em,
    }


def remover_artefato(chave, conn=None):
    conn, criada_internamente = _abrir_conexao(conn)
    cursor = conn.cursor()
    executar(conn, cursor, "DELETE FROM artefatos_sistema WHERE chave = ?", (chave,))
    conn.commit()

    if criada_internamente:
        conn.close()
