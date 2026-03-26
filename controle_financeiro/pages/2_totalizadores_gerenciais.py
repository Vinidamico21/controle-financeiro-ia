import pandas as pd
import streamlit as st

from database.db import conectar
from database.models import criar_tabela
from database.repository import buscar_transacoes
from reports.manager_dashboard import (
    aplicar_filtros,
    comparativo_mensal,
    fluxo_diario,
    indicadores_gerenciais,
    maiores_despesas,
    maiores_entradas,
    matriz_categoria_mes,
    opcoes_filtros,
    preparar_dashboard_gerencial,
    resumo_operacional,
    resumo_por_categoria,
    resumo_por_tipo,
)


st.set_page_config(page_title="Totalizadores Gerenciais", layout="wide")

conn = conectar()
criar_tabela(conn)


def formatar_moeda(valor):
    if valor is None or pd.isna(valor):
        return "-"

    sinal = "-" if float(valor) < 0 else ""
    valor_formatado = f"{abs(float(valor)):,.2f}".replace(",", "X").replace(".", ",")
    valor_formatado = valor_formatado.replace("X", ".")
    return f"{sinal}R$ {valor_formatado}"


def formatar_percentual(valor):
    if valor is None or pd.isna(valor):
        return "-"

    return f"{float(valor):.1%}"


def formatar_data(valor):
    if valor is None or pd.isna(valor):
        return "-"

    return pd.to_datetime(valor).strftime("%d/%m/%Y")


def estilizar_dataframe(df, colunas_monetarias=None):
    colunas_monetarias = colunas_monetarias or []
    formatos = {coluna: formatar_moeda for coluna in colunas_monetarias if coluna in df.columns}

    if "data" in df.columns:
        formatos["data"] = formatar_data

    return df.style.format(formatos)


historico = buscar_transacoes(conn)
df_dashboard = preparar_dashboard_gerencial(historico)

st.title("Totalizadores Gerenciais")
st.caption(
    "Painel executivo para leitura de resultado, comportamento das despesas, "
    "qualidade operacional e composição do fluxo financeiro."
)

if df_dashboard.empty:
    st.info("Ainda nao ha dados salvos suficientes para montar os totalizadores gerenciais.")
    st.stop()

filtros = opcoes_filtros(df_dashboard)

with st.expander("Filtros gerenciais", expanded=True):
    col1, col2, col3 = st.columns(3)
    anos = col1.multiselect("Ano", filtros["anos"])
    meses = col2.multiselect("Mes", filtros["meses"])
    categorias = col3.multiselect("Categoria", filtros["categorias"])

    col4, col5, col6 = st.columns(3)
    tipos = col4.multiselect("Tipo de movimentacao", filtros["tipos"])
    status = col5.multiselect("Status", filtros["status"])
    origens = col6.multiselect("Origem da classificacao", filtros["origens"])

    col7, col8 = st.columns(2)
    somente_revisados = col7.checkbox("Somente revisados manualmente")
    somente_pendentes = col8.checkbox("Somente pendentes de revisao")

df_filtrado = aplicar_filtros(
    df_dashboard,
    anos=anos,
    meses=meses,
    categorias=categorias,
    tipos=tipos,
    status=status,
    origens=origens,
    somente_revisados=somente_revisados,
    somente_pendentes=somente_pendentes,
)

if df_filtrado.empty:
    st.warning("Nenhum registro encontrado com os filtros selecionados.")
    st.stop()

metricas = indicadores_gerenciais(df_filtrado)

linha1 = st.columns(4)
linha1[0].metric("Entradas", formatar_moeda(metricas["entradas"]))
linha1[1].metric("Saidas", formatar_moeda(-metricas["saidas"]))
linha1[2].metric("Saldo", formatar_moeda(metricas["saldo"]))
linha1[3].metric("Transacoes", metricas["quantidade"])

linha2 = st.columns(4)
linha2[0].metric("Ticket medio saida", formatar_moeda(-metricas["ticket_medio_saida"]))
linha2[1].metric("Ticket medio entrada", formatar_moeda(metricas["ticket_medio_entrada"]))
linha2[2].metric("Taxa de revisao", formatar_percentual(metricas["taxa_revisao"]))
linha2[3].metric("Pendencias", metricas["pendencias"])

st.subheader("Visao executiva")
df_mensal = comparativo_mensal(df_filtrado)

if not df_mensal.empty:
    st.dataframe(
        estilizar_dataframe(df_mensal, ["entradas", "saidas", "saldo"]),
        hide_index=True,
        use_container_width=True,
    )

    graf1, graf2 = st.columns(2)
    with graf1:
        st.caption("Entradas x saídas por mes")
        st.bar_chart(df_mensal.set_index("mes_nome")[["entradas", "saidas"]])
    with graf2:
        st.caption("Saldo por mes")
        st.line_chart(df_mensal.set_index("mes_nome")["saldo"])

st.subheader("Composicao do resultado")
df_categoria = resumo_por_categoria(df_filtrado)
df_tipo = resumo_por_tipo(df_filtrado)

comp1, comp2 = st.columns(2)
with comp1:
    st.caption("Resultado por categoria")
    st.dataframe(
        estilizar_dataframe(df_categoria, ["entradas", "saidas", "saldo"]),
        hide_index=True,
        use_container_width=True,
    )
    if not df_categoria.empty:
        st.bar_chart(df_categoria.set_index("categoria")["saidas"])

with comp2:
    st.caption("Resultado por tipo de movimentacao")
    st.dataframe(
        estilizar_dataframe(df_tipo, ["entradas", "saidas", "saldo"]),
        hide_index=True,
        use_container_width=True,
    )
    if not df_tipo.empty:
        st.bar_chart(df_tipo.set_index("tipo_movimentacao")[["entradas", "saidas"]])

st.subheader("Fluxo e concentracao")
df_fluxo = fluxo_diario(df_filtrado)
df_top_despesas = maiores_despesas(df_filtrado)
df_top_entradas = maiores_entradas(df_filtrado)

fluxo1, fluxo2 = st.columns(2)
with fluxo1:
    st.caption("Fluxo diario")
    if df_fluxo.empty:
        st.info("Nao ha datas suficientes para essa visualizacao.")
    else:
        st.dataframe(
            estilizar_dataframe(df_fluxo, ["entradas", "saidas", "saldo"]),
            hide_index=True,
            use_container_width=True,
        )
        st.line_chart(df_fluxo.set_index("dia_label")["saldo"])

with fluxo2:
    st.caption("Matriz categoria x mes")
    df_matriz = matriz_categoria_mes(df_filtrado)
    if df_matriz.empty:
        st.info("Nao ha dados suficientes para montar a matriz.")
    else:
        st.dataframe(
            df_matriz.style.format(formatar_moeda),
            use_container_width=True,
        )

st.subheader("Maiores movimentacoes")
mov1, mov2 = st.columns(2)
with mov1:
    st.caption("Top despesas")
    if df_top_despesas.empty:
        st.info("Nao ha despesas no recorte atual.")
    else:
        st.dataframe(
            estilizar_dataframe(df_top_despesas, ["saida"]),
            hide_index=True,
            use_container_width=True,
        )

with mov2:
    st.caption("Top entradas")
    if df_top_entradas.empty:
        st.info("Nao ha entradas no recorte atual.")
    else:
        st.dataframe(
            estilizar_dataframe(df_top_entradas, ["entrada"]),
            hide_index=True,
            use_container_width=True,
        )

st.subheader("Leitura operacional")
df_operacional = resumo_operacional(df_filtrado)

if df_operacional.empty:
    st.info("Sem dados operacionais no recorte atual.")
else:
    col_op1, col_op2 = st.columns(2)
    with col_op1:
        df_status = df_operacional[df_operacional["grupo"] == "Status"].copy()
        if not df_status.empty:
            st.caption("Distribuicao por status")
            st.dataframe(df_status, hide_index=True, use_container_width=True)
            st.bar_chart(df_status.set_index("valor")["quantidade"])
    with col_op2:
        df_origem = df_operacional[df_operacional["grupo"] == "Origem"].copy()
        if not df_origem.empty:
            st.caption("Distribuicao por origem da classificacao")
            st.dataframe(df_origem, hide_index=True, use_container_width=True)
            st.bar_chart(df_origem.set_index("valor")["quantidade"])

st.subheader("Base detalhada filtrada")
colunas_detalhe = [
    "data",
    "descricao",
    "tipo_movimentacao",
    "categoria",
    "status",
    "origem",
    "valor_corrigido",
]
colunas_existentes = [coluna for coluna in colunas_detalhe if coluna in df_filtrado.columns]
st.dataframe(
    estilizar_dataframe(df_filtrado[colunas_existentes], ["valor_corrigido"]),
    hide_index=True,
    use_container_width=True,
)
