import pandas as pd


def gerar_resumo(df):
    if df.empty:
        return pd.DataFrame(columns=["categoria", "valor", "percentual"])

    resumo = df.groupby("categoria", dropna=False)["valor"].sum().reset_index()
    total = resumo["valor"].sum()

    if total == 0:
        resumo["percentual"] = 0.0
    else:
        resumo["percentual"] = (resumo["valor"] / total) * 100

    return resumo.sort_values("valor", ascending=True).reset_index(drop=True)
