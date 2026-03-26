import pandas as pd


TODOS_OS_MESES = "Todos os meses"
MAPA_MESES = {
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


def preparar_dados_relatorio(df):
    if df is None or df.empty:
        return pd.DataFrame()

    base = df.copy()

    if "valor" not in base.columns and "valor_corrigido" in base.columns:
        base["valor"] = base["valor_corrigido"]

    if "valor_corrigido" in base.columns:
        base["valor"] = base["valor_corrigido"]

    if "categoria" not in base.columns:
        base["categoria"] = "Sem categoria"

    if "descricao" not in base.columns:
        base["descricao"] = ""

    base["valor"] = pd.to_numeric(base["valor"], errors="coerce").fillna(0.0)
    base["data"] = pd.to_datetime(base.get("data"), errors="coerce")
    base["entrada"] = base["valor"].where(base["valor"] > 0, 0.0)
    base["saida"] = (-base["valor"]).where(base["valor"] < 0, 0.0)
    base["saldo"] = base["valor"]
    base["mes_referencia"] = base["data"].dt.to_period("M")
    base["mes_label"] = base["data"].apply(formatar_mes_label)
    base.loc[base["mes_referencia"].isna(), "mes_label"] = "Sem data"
    base["dia_label"] = base["data"].dt.strftime("%d/%m/%Y")
    base.loc[base["data"].isna(), "dia_label"] = "Sem data"
    return base


def formatar_mes_label(data):
    if pd.isna(data):
        return "Sem data"

    return f"{MAPA_MESES[data.month]}/{data.year}"


def listar_meses(df):
    if df.empty:
        return [TODOS_OS_MESES]

    meses_validos = (
        df.loc[df["mes_label"] != "Sem data", "mes_label"]
        .dropna()
        .drop_duplicates()
        .tolist()
    )
    meses_validos = sorted(meses_validos, key=ordenar_mes_label, reverse=True)

    if "Sem data" in df["mes_label"].values:
        meses_validos.append("Sem data")

    return [TODOS_OS_MESES] + meses_validos


def filtrar_por_mes(df, mes_escolhido):
    if df.empty or mes_escolhido == TODOS_OS_MESES:
        return df.copy()

    return df[df["mes_label"] == mes_escolhido].copy()


def gerar_indicadores(df):
    if df.empty:
        return {
            "entradas": 0.0,
            "saidas": 0.0,
            "saldo": 0.0,
            "quantidade": 0,
            "ticket_medio_saida": 0.0,
        }

    saidas = df.loc[df["valor"] < 0, "valor"].abs()

    return {
        "entradas": float(df["entrada"].sum()),
        "saidas": float(df["saida"].sum()),
        "saldo": float(df["saldo"].sum()),
        "quantidade": int(len(df)),
        "ticket_medio_saida": float(saidas.mean()) if not saidas.empty else 0.0,
    }


def gerar_resumo_mensal(df):
    if df.empty:
        return pd.DataFrame(
            columns=["mes_label", "entradas", "saidas", "saldo", "quantidade"]
        )

    resumo = (
        df.groupby("mes_label", dropna=False)
        .agg(
            entradas=("entrada", "sum"),
            saidas=("saida", "sum"),
            saldo=("saldo", "sum"),
            quantidade=("descricao", "count"),
        )
        .reset_index()
    )

    resumo["ordem"] = resumo["mes_label"].where(
        resumo["mes_label"] != "Sem data",
        "0000-00",
    )
    resumo["ordem"] = resumo["mes_label"].map(ordenar_mes_label)
    resumo = resumo.sort_values("ordem").drop(columns=["ordem"])
    return resumo.reset_index(drop=True)


def ordenar_mes_label(mes_label):
    if mes_label == "Sem data":
        return "0000-00"

    mes_texto, ano = mes_label.split("/")
    mes_numero = {valor: chave for chave, valor in MAPA_MESES.items()}[mes_texto]
    return f"{ano}-{mes_numero:02d}"


def gerar_resumo_categorias(df):
    if df.empty:
        return pd.DataFrame(
            columns=["categoria", "entradas", "saidas", "saldo", "quantidade"]
        )

    resumo = (
        df.groupby("categoria", dropna=False)
        .agg(
            entradas=("entrada", "sum"),
            saidas=("saida", "sum"),
            saldo=("saldo", "sum"),
            quantidade=("descricao", "count"),
        )
        .reset_index()
    )

    return resumo.sort_values(["saidas", "entradas"], ascending=False).reset_index(
        drop=True
    )


def gerar_fluxo_diario(df):
    if df.empty:
        return pd.DataFrame(columns=["dia_label", "entradas", "saidas", "saldo"])

    base = df[df["data"].notna()].copy()

    if base.empty:
        return pd.DataFrame(columns=["dia_label", "entradas", "saidas", "saldo"])

    fluxo = (
        base.groupby(["data", "dia_label"], dropna=False)
        .agg(
            entradas=("entrada", "sum"),
            saidas=("saida", "sum"),
            saldo=("saldo", "sum"),
        )
        .reset_index()
        .sort_values("data")
    )

    return fluxo.drop(columns=["data"]).reset_index(drop=True)
