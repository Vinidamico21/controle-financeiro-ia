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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            descricao TEXT,
            valor REAL,
            categoria TEXT,
            status TEXT
        )
        """
    )

    cursor.execute("PRAGMA table_info(transacoes)")
    colunas_existentes = {coluna[1] for coluna in cursor.fetchall()}

    for coluna, tipo in COLUNAS_ADICIONAIS.items():
        if coluna not in colunas_existentes:
            cursor.execute(f"ALTER TABLE transacoes ADD COLUMN {coluna} {tipo}")

    conn.commit()
