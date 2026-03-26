import pandas as pd

from services.categorizer import CATEGORIA_NAO_CLASSIFICADA
from services.ml_classifier import CONFIANCA_MINIMA_PADRAO, CONFIANCA_MINIMA_TIPO


def construir_dataframe_historico(historico):
    if not historico:
        return pd.DataFrame()

    df = pd.DataFrame(historico).copy()

    for coluna in [
        "valor",
        "valor_original",
        "valor_corrigido",
        "confianca",
        "confianca_tipo",
        "revisado_usuario",
        "id",
    ]:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    for coluna in [
        "categoria",
        "categoria_prevista",
        "tipo_movimentacao",
        "tipo_previsto",
        "status",
        "origem",
        "alerta_revisao",
    ]:
        if coluna not in df.columns:
            df[coluna] = None

    if "valor_corrigido" not in df.columns:
        df["valor_corrigido"] = df.get("valor")

    if "valor_original" not in df.columns:
        df["valor_original"] = df.get("valor")

    df["revisado_usuario"] = df["revisado_usuario"].fillna(0).astype(int)
    df["corrigiu_valor"] = (
        df["valor_original"].round(2) != df["valor_corrigido"].round(2)
    )
    df["corrigiu_tipo"] = (
        df["tipo_previsto"].fillna("") != df["tipo_movimentacao"].fillna("")
    )
    df["corrigiu_categoria"] = (
        df["categoria_prevista"].fillna("") != df["categoria"].fillna("")
    ) & df["categoria_prevista"].notna()
    df["baixa_confianca_categoria"] = df["confianca"].fillna(0) < CONFIANCA_MINIMA_PADRAO
    df["baixa_confianca_tipo"] = df["confianca_tipo"].fillna(0) < CONFIANCA_MINIMA_TIPO
    df["nao_classificado"] = df["categoria"].fillna("") == CATEGORIA_NAO_CLASSIFICADA
    df["magnitude_valor"] = df["valor_corrigido"].abs()
    return df


def calcular_metricas_gerais(df):
    if df.empty:
        return {
            "total_transacoes": 0,
            "total_revisadas": 0,
            "taxa_revisao": 0.0,
            "taxa_auto": 0.0,
            "itens_baixa_confianca": 0,
            "itens_pendentes": 0,
            "ajustes_valor": 0,
            "ajustes_tipo": 0,
            "ajustes_categoria": 0,
        }

    total = len(df)
    total_revisadas = int(df["revisado_usuario"].sum())
    auto = int((df["status"] == "AUTO").sum())
    baixa_confianca = int(
        (df["baixa_confianca_categoria"] | df["baixa_confianca_tipo"]).sum()
    )
    pendentes = int((df["status"] == "PENDENTE_REVISAO").sum())

    return {
        "total_transacoes": total,
        "total_revisadas": total_revisadas,
        "taxa_revisao": total_revisadas / total if total else 0.0,
        "taxa_auto": auto / total if total else 0.0,
        "itens_baixa_confianca": baixa_confianca,
        "itens_pendentes": pendentes,
        "ajustes_valor": int(df["corrigiu_valor"].sum()),
        "ajustes_tipo": int(df["corrigiu_tipo"].sum()),
        "ajustes_categoria": int(df["corrigiu_categoria"].sum()),
    }


def resumo_origem(df):
    if df.empty:
        return pd.DataFrame(columns=["origem", "quantidade"])

    return (
        df["origem"]
        .fillna("DESCONHECIDA")
        .value_counts()
        .rename_axis("origem")
        .reset_index(name="quantidade")
    )


def confusoes_categoria(df):
    if df.empty:
        return pd.DataFrame(columns=["categoria_prevista", "categoria", "quantidade"])

    base = df[
        df["categoria_prevista"].notna()
        & (df["categoria_prevista"] != "")
        & (df["categoria_prevista"] != df["categoria"])
    ]

    if base.empty:
        return pd.DataFrame(columns=["categoria_prevista", "categoria", "quantidade"])

    return (
        base.groupby(["categoria_prevista", "categoria"])
        .size()
        .reset_index(name="quantidade")
        .sort_values("quantidade", ascending=False)
    )


def confusoes_tipo(df):
    if df.empty:
        return pd.DataFrame(columns=["tipo_previsto", "tipo_movimentacao", "quantidade"])

    base = df[
        df["tipo_previsto"].notna()
        & (df["tipo_previsto"] != "")
        & (df["tipo_previsto"] != df["tipo_movimentacao"])
    ]

    if base.empty:
        return pd.DataFrame(columns=["tipo_previsto", "tipo_movimentacao", "quantidade"])

    return (
        base.groupby(["tipo_previsto", "tipo_movimentacao"])
        .size()
        .reset_index(name="quantidade")
        .sort_values("quantidade", ascending=False)
    )


def categorias_com_mais_revisao(df):
    if df.empty:
        return pd.DataFrame(columns=["categoria", "revisoes"])

    base = df[df["revisado_usuario"] == 1]

    if base.empty:
        return pd.DataFrame(columns=["categoria", "revisoes"])

    return (
        base["categoria"]
        .fillna("Sem categoria")
        .value_counts()
        .rename_axis("categoria")
        .reset_index(name="revisoes")
    )


def tipos_com_mais_revisao(df):
    if df.empty:
        return pd.DataFrame(columns=["tipo_movimentacao", "revisoes"])

    base = df[df["corrigiu_tipo"]]

    if base.empty:
        return pd.DataFrame(columns=["tipo_movimentacao", "revisoes"])

    return (
        base["tipo_movimentacao"]
        .fillna("Sem tipo")
        .value_counts()
        .rename_axis("tipo_movimentacao")
        .reset_index(name="revisoes")
    )


def itens_baixa_confianca(df, limite=15):
    if df.empty:
        return pd.DataFrame()

    base = df[df["baixa_confianca_categoria"] | df["baixa_confianca_tipo"]].copy()

    if base.empty:
        return pd.DataFrame()

    colunas = [
        "descricao",
        "categoria",
        "categoria_prevista",
        "confianca",
        "tipo_movimentacao",
        "tipo_previsto",
        "confianca_tipo",
        "status",
        "alerta_revisao",
    ]

    return base[colunas].head(limite)


def itens_com_ajuste_valor(df, limite=15):
    if df.empty:
        return pd.DataFrame()

    base = df[df["corrigiu_valor"]].copy()

    if base.empty:
        return pd.DataFrame()

    colunas = [
        "descricao",
        "tipo_movimentacao",
        "valor_original",
        "valor_corrigido",
        "categoria",
        "status",
        "alerta_revisao",
    ]
    return base[colunas].head(limite)


def fila_rotulacao(df, limite=15):
    if df.empty:
        return pd.DataFrame()

    base = df[
        df["nao_classificado"]
        | (df["status"] == "PENDENTE_REVISAO")
        | df["baixa_confianca_categoria"]
        | df["baixa_confianca_tipo"]
    ].copy()

    if base.empty:
        return pd.DataFrame()

    colunas = [
        "descricao",
        "categoria",
        "tipo_movimentacao",
        "status",
        "confianca",
        "confianca_tipo",
        "alerta_revisao",
    ]
    return base[colunas].head(limite)


def tendencia_revisao(df, tamanho_janela=20):
    if df.empty or "id" not in df.columns:
        return pd.DataFrame(columns=["bloco", "taxa_revisao"])

    base = df.sort_values("id").reset_index(drop=True).copy()
    base["bloco"] = (base.index // tamanho_janela) + 1

    return (
        base.groupby("bloco")["revisado_usuario"]
        .mean()
        .reset_index(name="taxa_revisao")
    )


def resumo_status(df):
    if df.empty:
        return pd.DataFrame(columns=["status", "quantidade"])

    return (
        df["status"]
        .fillna("SEM_STATUS")
        .value_counts()
        .rename_axis("status")
        .reset_index(name="quantidade")
    )
