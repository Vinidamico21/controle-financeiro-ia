import pandas as pd

from reports.report import preparar_dados_relatorio

MAPA_MESES_PT = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


def preparar_dashboard_gerencial(historico):
    if not historico:
        return pd.DataFrame()

    df = preparar_dados_relatorio(pd.DataFrame(historico))

    if df.empty:
        return df

    df["categoria"] = df["categoria"].fillna("Sem categoria")
    df["tipo_movimentacao"] = df["tipo_movimentacao"].fillna("Sem tipo")
    df["status"] = df["status"].fillna("Sem status")
    df["origem"] = df["origem"].fillna("Sem origem")
    df["revisado_usuario"] = pd.to_numeric(
        df.get("revisado_usuario"),
        errors="coerce",
    ).fillna(0).astype(int)
    df["ano"] = df["data"].dt.year.astype("Int64")
    df["mes_numero"] = df["data"].dt.month.astype("Int64")
    df["mes_nome"] = df.apply(formatar_mes_nome, axis=1)
    df.loc[df["data"].isna(), "mes_nome"] = "Sem data"
    df["dia_semana"] = df["data"].dt.day_name()
    df.loc[df["data"].isna(), "dia_semana"] = "Sem data"
    df["despesa_absoluta"] = df["saida"]
    df["entrada_absoluta"] = df["entrada"]
    return df


def formatar_mes_nome(linha):
    data = linha.get("data")

    if pd.isna(data):
        return "Sem data"

    return f"{MAPA_MESES_PT[int(data.month)]}/{int(data.year)}"


def opcoes_filtros(df):
    if df.empty:
        return {
            "anos": [],
            "meses": [],
            "categorias": [],
            "tipos": [],
            "status": [],
            "origens": [],
        }

    anos = sorted(df["ano"].dropna().astype(int).unique().tolist(), reverse=True)
    meses = (
        df.loc[df["mes_nome"] != "Sem data", ["ano", "mes_numero", "mes_nome"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["ano", "mes_numero"], ascending=[False, False])["mes_nome"]
        .tolist()
    )
    categorias = sorted(df["categoria"].dropna().unique().tolist())
    tipos = sorted(df["tipo_movimentacao"].dropna().unique().tolist())
    status = sorted(df["status"].dropna().unique().tolist())
    origens = sorted(df["origem"].dropna().unique().tolist())
    return {
        "anos": anos,
        "meses": meses,
        "categorias": categorias,
        "tipos": tipos,
        "status": status,
        "origens": origens,
    }


def aplicar_filtros(
    df,
    anos=None,
    meses=None,
    categorias=None,
    tipos=None,
    status=None,
    origens=None,
    somente_revisados=False,
    somente_pendentes=False,
):
    if df.empty:
        return df.copy()

    base = df.copy()

    if anos:
        base = base[base["ano"].isin(anos)]

    if meses:
        base = base[base["mes_nome"].isin(meses)]

    if categorias:
        base = base[base["categoria"].isin(categorias)]

    if tipos:
        base = base[base["tipo_movimentacao"].isin(tipos)]

    if status:
        base = base[base["status"].isin(status)]

    if origens:
        base = base[base["origem"].isin(origens)]

    if somente_revisados:
        base = base[base["revisado_usuario"] == 1]

    if somente_pendentes:
        base = base[base["status"] == "PENDENTE_REVISAO"]

    return base.copy()


def indicadores_gerenciais(df):
    if df.empty:
        return {
            "entradas": 0.0,
            "saidas": 0.0,
            "saldo": 0.0,
            "quantidade": 0,
            "ticket_medio_saida": 0.0,
            "ticket_medio_entrada": 0.0,
            "taxa_revisao": 0.0,
            "pendencias": 0,
        }

    despesas = df.loc[df["saida"] > 0, "saida"]
    entradas = df.loc[df["entrada"] > 0, "entrada"]
    return {
        "entradas": float(df["entrada"].sum()),
        "saidas": float(df["saida"].sum()),
        "saldo": float(df["saldo"].sum()),
        "quantidade": int(len(df)),
        "ticket_medio_saida": float(despesas.mean()) if not despesas.empty else 0.0,
        "ticket_medio_entrada": float(entradas.mean()) if not entradas.empty else 0.0,
        "taxa_revisao": float(df["revisado_usuario"].mean()) if len(df) else 0.0,
        "pendencias": int((df["status"] == "PENDENTE_REVISAO").sum()),
    }


def comparativo_mensal(df):
    if df.empty:
        return pd.DataFrame(
            columns=["mes_nome", "entradas", "saidas", "saldo", "quantidade"]
        )

    base = (
        df.groupby(["ano", "mes_numero", "mes_nome"], dropna=False)
        .agg(
            entradas=("entrada", "sum"),
            saidas=("saida", "sum"),
            saldo=("saldo", "sum"),
            quantidade=("descricao", "count"),
        )
        .reset_index()
    )

    base["ordem"] = (
        base["ano"].fillna(0).astype(int).astype(str)
        + "-"
        + base["mes_numero"].fillna(0).astype(int).astype(str).str.zfill(2)
    )
    base = base.sort_values("ordem").drop(columns=["ordem", "ano", "mes_numero"])
    return base.reset_index(drop=True)


def resumo_por_categoria(df):
    if df.empty:
        return pd.DataFrame(
            columns=["categoria", "entradas", "saidas", "saldo", "quantidade"]
        )

    return (
        df.groupby("categoria", dropna=False)
        .agg(
            entradas=("entrada", "sum"),
            saidas=("saida", "sum"),
            saldo=("saldo", "sum"),
            quantidade=("descricao", "count"),
        )
        .reset_index()
        .sort_values(["saidas", "entradas"], ascending=False)
        .reset_index(drop=True)
    )


def resumo_por_tipo(df):
    if df.empty:
        return pd.DataFrame(
            columns=["tipo_movimentacao", "entradas", "saidas", "saldo", "quantidade"]
        )

    return (
        df.groupby("tipo_movimentacao", dropna=False)
        .agg(
            entradas=("entrada", "sum"),
            saidas=("saida", "sum"),
            saldo=("saldo", "sum"),
            quantidade=("descricao", "count"),
        )
        .reset_index()
        .sort_values(["saidas", "entradas"], ascending=False)
        .reset_index(drop=True)
    )


def resumo_operacional(df):
    if df.empty:
        return pd.DataFrame(columns=["grupo", "valor", "quantidade"])

    status = (
        df["status"]
        .value_counts()
        .rename_axis("valor")
        .reset_index(name="quantidade")
        .assign(grupo="Status")
    )
    origem = (
        df["origem"]
        .value_counts()
        .rename_axis("valor")
        .reset_index(name="quantidade")
        .assign(grupo="Origem")
    )
    return pd.concat([status, origem], ignore_index=True)


def fluxo_diario(df):
    if df.empty:
        return pd.DataFrame(columns=["dia_label", "entradas", "saidas", "saldo"])

    base = df[df["data"].notna()].copy()

    if base.empty:
        return pd.DataFrame(columns=["dia_label", "entradas", "saidas", "saldo"])

    return (
        base.groupby(["data", "dia_label"], dropna=False)
        .agg(
            entradas=("entrada", "sum"),
            saidas=("saida", "sum"),
            saldo=("saldo", "sum"),
        )
        .reset_index()
        .sort_values("data")
        .drop(columns=["data"])
        .reset_index(drop=True)
    )


def maiores_despesas(df, limite=15):
    if df.empty:
        return pd.DataFrame(
            columns=["data", "descricao", "categoria", "tipo_movimentacao", "saida"]
        )

    base = df[df["saida"] > 0].copy()

    if base.empty:
        return pd.DataFrame(
            columns=["data", "descricao", "categoria", "tipo_movimentacao", "saida"]
        )

    return (
        base.sort_values("saida", ascending=False)[
            ["data", "descricao", "categoria", "tipo_movimentacao", "saida"]
        ]
        .head(limite)
        .reset_index(drop=True)
    )


def maiores_entradas(df, limite=15):
    if df.empty:
        return pd.DataFrame(
            columns=["data", "descricao", "categoria", "tipo_movimentacao", "entrada"]
        )

    base = df[df["entrada"] > 0].copy()

    if base.empty:
        return pd.DataFrame(
            columns=["data", "descricao", "categoria", "tipo_movimentacao", "entrada"]
        )

    return (
        base.sort_values("entrada", ascending=False)[
            ["data", "descricao", "categoria", "tipo_movimentacao", "entrada"]
        ]
        .head(limite)
        .reset_index(drop=True)
    )


def matriz_categoria_mes(df):
    if df.empty:
        return pd.DataFrame()

    pivot = pd.pivot_table(
        df,
        index="categoria",
        columns="mes_nome",
        values="saldo",
        aggfunc="sum",
        fill_value=0.0,
    )

    if pivot.empty:
        return pd.DataFrame()

    return pivot
