from database.db import e_postgres, executar
from services.categorizer import CATEGORIA_NAO_CLASSIFICADA


def salvar_transacoes(conn, transacoes):
    cursor = conn.cursor()

    for transacao in transacoes:
        categoria_prevista = transacao.get("categoria_prevista", transacao["categoria"])
        tipo_previsto = transacao.get(
            "tipo_previsto",
            transacao.get("tipo_movimentacao"),
        )
        valor_original = transacao.get("valor_original", transacao["valor"])
        valor_final = transacao.get("valor_corrigido", transacao["valor"])

        revisado_usuario = int(
            transacao["categoria"] != categoria_prevista
            or transacao.get("tipo_movimentacao") != tipo_previsto
            or round(float(valor_final), 2) != round(float(valor_original), 2)
        )

        if transacao["categoria"] == CATEGORIA_NAO_CLASSIFICADA:
            status = "PENDENTE_REVISAO"
        elif revisado_usuario:
            status = "REVISADO"
        else:
            status = "AUTO"

        executar(
            conn,
            cursor,
            """
            INSERT INTO transacoes (
                data,
                descricao,
                valor,
                categoria,
                status,
                origem,
                confianca,
                categoria_prevista,
                tipo_movimentacao,
                tipo_previsto,
                confianca_tipo,
                valor_original,
                valor_corrigido,
                revisado_usuario,
                alerta_revisao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transacao.get("data"),
                transacao["descricao"],
                valor_final,
                transacao["categoria"],
                status,
                transacao.get("origem", "MANUAL"),
                transacao.get("confianca"),
                categoria_prevista,
                transacao.get("tipo_movimentacao"),
                tipo_previsto,
                transacao.get("confianca_tipo"),
                valor_original,
                valor_final,
                revisado_usuario,
                transacao.get("alerta_revisao"),
            ),
        )

    conn.commit()


def buscar_transacoes(conn):
    cursor = conn.cursor()
    executar(
        conn,
        cursor,
        """
        SELECT
            id,
            data,
            descricao,
            valor,
            categoria,
            origem,
            confianca,
            categoria_prevista,
            status,
            tipo_movimentacao,
            tipo_previsto,
            confianca_tipo,
            valor_original,
            valor_corrigido,
            revisado_usuario,
            alerta_revisao
        FROM transacoes
        ORDER BY COALESCE(data, '') DESC, id DESC
        """
    )
    colunas = [
        "id",
        "data",
        "descricao",
        "valor",
        "categoria",
        "origem",
        "confianca",
        "categoria_prevista",
        "status",
        "tipo_movimentacao",
        "tipo_previsto",
        "confianca_tipo",
        "valor_original",
        "valor_corrigido",
        "revisado_usuario",
        "alerta_revisao",
    ]
    return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


def buscar_base_treinamento(conn):
    cursor = conn.cursor()
    executar(
        conn,
        cursor,
        """
        SELECT descricao, categoria, tipo_movimentacao
        FROM transacoes
        WHERE descricao IS NOT NULL
          AND descricao != ''
        ORDER BY id DESC
        """
    )
    colunas = ["descricao", "categoria", "tipo_movimentacao"]
    return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


def limpar_transacoes(conn):
    cursor = conn.cursor()

    if e_postgres(conn):
        executar(conn, cursor, "TRUNCATE TABLE transacoes RESTART IDENTITY")
    else:
        executar(conn, cursor, "DELETE FROM transacoes")
        executar(conn, cursor, "DELETE FROM sqlite_sequence WHERE name = ?", ("transacoes",))

    conn.commit()
