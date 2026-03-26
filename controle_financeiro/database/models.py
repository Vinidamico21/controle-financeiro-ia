from database.db import buscar_colunas_tabela, e_postgres, executar


COLUNAS_ADICIONAIS = {
    "origem": "TEXT",
    "confianca": "REAL",
    "categoria_prevista": "TEXT",
    "tipo_movimentacao": "TEXT",
    "tipo_previsto": "TEXT",
    "confianca_tipo": "REAL",
    "valor_original": "REAL",
    "valor_corrigido": "REAL",
    "revisado_usuario": "INTEGER DEFAULT 0",
    "alerta_revisao": "TEXT",
}


def criar_tabela(conn):
    cursor = conn.cursor()

    definicao_id = "BIGSERIAL PRIMARY KEY" if e_postgres(conn) else "INTEGER PRIMARY KEY AUTOINCREMENT"
    blob_type = "BYTEA" if e_postgres(conn) else "BLOB"

    executar(
        conn,
        cursor,
        f"""
        CREATE TABLE IF NOT EXISTS transacoes (
            id {definicao_id},
            data TEXT,
            descricao TEXT,
            valor REAL,
            categoria TEXT,
            status TEXT
        )
        """,
    )

    executar(
        conn,
        cursor,
        f"""
        CREATE TABLE IF NOT EXISTS artefatos_sistema (
            chave TEXT PRIMARY KEY,
            payload {blob_type} NOT NULL,
            metadata TEXT,
            atualizado_em TEXT
        )
        """,
    )

    colunas_existentes = buscar_colunas_tabela(conn, "transacoes")

    for coluna, tipo in COLUNAS_ADICIONAIS.items():
        if coluna not in colunas_existentes:
            executar(
                conn,
                cursor,
                f"ALTER TABLE transacoes ADD COLUMN {coluna} {tipo}",
            )

    conn.commit()
