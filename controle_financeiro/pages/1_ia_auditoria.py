import pandas as pd
import streamlit as st

from database.db import conectar
from database.models import criar_tabela
from database.repository import buscar_transacoes
from reports.ai_audit import (
    calcular_metricas_gerais,
    categorias_com_mais_revisao,
    confusoes_categoria,
    confusoes_tipo,
    construir_dataframe_historico,
    fila_rotulacao,
    itens_baixa_confianca,
    itens_com_ajuste_valor,
    resumo_origem,
    resumo_status,
    tendencia_revisao,
    tipos_com_mais_revisao,
)
from services.ml_classifier import obter_status_modelo


st.set_page_config(page_title="Auditoria da IA", layout="wide")

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


def estilizar_valores(df, colunas_monetarias=None):
    colunas_monetarias = colunas_monetarias or []
    formatos = {coluna: formatar_moeda for coluna in colunas_monetarias if coluna in df.columns}
    return df.style.format(formatos)


historico = buscar_transacoes(conn)
df_historico = construir_dataframe_historico(historico)
metricas = calcular_metricas_gerais(df_historico)
status_modelo = obter_status_modelo()

st.title("Auditoria da IA")
st.caption(
    "Esta tela mostra onde a inteligencia esta acertando, onde ainda exige revisao "
    "manual e quais exemplos valem mais para melhorar o treino."
)

if df_historico.empty:
    st.info("Ainda nao ha historico suficiente para auditar. Salve algumas transacoes primeiro.")
    st.stop()

linha1 = st.columns(4)
linha1[0].metric("Transacoes auditadas", metricas["total_transacoes"])
linha1[1].metric("Taxa de revisao", formatar_percentual(metricas["taxa_revisao"]))
linha1[2].metric("Taxa automatica", formatar_percentual(metricas["taxa_auto"]))
linha1[3].metric("Baixa confianca", metricas["itens_baixa_confianca"])

linha2 = st.columns(4)
linha2[0].metric("Pendentes", metricas["itens_pendentes"])
linha2[1].metric("Ajustes de valor", metricas["ajustes_valor"])
linha2[2].metric("Ajustes de tipo", metricas["ajustes_tipo"])
linha2[3].metric("Ajustes de categoria", metricas["ajustes_categoria"])

st.subheader("Estado atual do modelo")
modelo_col1, modelo_col2, modelo_col3 = st.columns(3)
modelo_col1.metric("Amostras de categoria", status_modelo.get("total_amostras", 0))
modelo_col2.metric("Amostras de Entrada/Saida", status_modelo.get("total_amostras_tipo", 0))
modelo_col3.metric(
    "Acuracia de tipo",
    formatar_percentual(status_modelo.get("acuracia_tipo")),
)

if status_modelo.get("categorias"):
    st.caption("Categorias aprendidas: " + ", ".join(status_modelo["categorias"]))

if status_modelo.get("tipos"):
    st.caption("Tipos aprendidos: " + ", ".join(status_modelo["tipos"]))

st.subheader("Panorama operacional")
panorama1, panorama2 = st.columns(2)

with panorama1:
    df_status = resumo_status(df_historico)
    st.dataframe(df_status, hide_index=True, use_container_width=True)
    if not df_status.empty:
        st.bar_chart(df_status.set_index("status")["quantidade"])

with panorama2:
    df_origem = resumo_origem(df_historico)
    st.dataframe(df_origem, hide_index=True, use_container_width=True)
    if not df_origem.empty:
        st.bar_chart(df_origem.set_index("origem")["quantidade"])

st.subheader("Onde a IA mais e corrigida")
correcoes1, correcoes2 = st.columns(2)

with correcoes1:
    df_confusoes_categoria = confusoes_categoria(df_historico)
    if df_confusoes_categoria.empty:
        st.info("Ainda nao ha correcoes de categoria suficientes para mapear confusoes.")
    else:
        st.dataframe(df_confusoes_categoria, hide_index=True, use_container_width=True)

with correcoes2:
    df_confusoes_tipo = confusoes_tipo(df_historico)
    if df_confusoes_tipo.empty:
        st.info("Ainda nao ha correcoes de Entrada/Saida suficientes para mapear confusoes.")
    else:
        st.dataframe(df_confusoes_tipo, hide_index=True, use_container_width=True)

st.subheader("Categorias e tipos com mais revisao")
revisoes1, revisoes2 = st.columns(2)

with revisoes1:
    df_categorias_revisadas = categorias_com_mais_revisao(df_historico)
    if df_categorias_revisadas.empty:
        st.info("Nenhuma categoria revisada ate agora.")
    else:
        st.dataframe(df_categorias_revisadas, hide_index=True, use_container_width=True)
        st.bar_chart(df_categorias_revisadas.set_index("categoria")["revisoes"])

with revisoes2:
    df_tipos_revisados = tipos_com_mais_revisao(df_historico)
    if df_tipos_revisados.empty:
        st.info("Nenhuma correcao de Entrada/Saida registrada ate agora.")
    else:
        st.dataframe(df_tipos_revisados, hide_index=True, use_container_width=True)
        st.bar_chart(df_tipos_revisados.set_index("tipo_movimentacao")["revisoes"])

st.subheader("Fila de melhoria")
fila1, fila2 = st.columns(2)

with fila1:
    df_baixa_confianca = itens_baixa_confianca(df_historico)
    if df_baixa_confianca.empty:
        st.success("Nenhum item salvo com baixa confianca no momento.")
    else:
        st.dataframe(df_baixa_confianca, hide_index=True, use_container_width=True)

with fila2:
    df_fila = fila_rotulacao(df_historico)
    if df_fila.empty:
        st.success("Nao ha fila critica de rotulacao no momento.")
    else:
        st.dataframe(df_fila, hide_index=True, use_container_width=True)

st.subheader("Sinais de problema no parser ou no valor")
df_ajustes_valor = itens_com_ajuste_valor(df_historico)

if df_ajustes_valor.empty:
    st.success("Nenhum ajuste manual de valor registrado ate agora.")
else:
    st.dataframe(
        estilizar_valores(
            df_ajustes_valor,
            colunas_monetarias=["valor_original", "valor_corrigido"],
        ),
        hide_index=True,
        use_container_width=True,
    )

st.subheader("Tendencia de revisao por blocos")
df_tendencia = tendencia_revisao(df_historico)

if df_tendencia.empty:
    st.info("Ainda nao ha volume suficiente para observar tendencia de revisao.")
else:
    df_tendencia["taxa_revisao"] = df_tendencia["taxa_revisao"].fillna(0)
    st.dataframe(
        df_tendencia.assign(
            taxa_revisao=df_tendencia["taxa_revisao"].map(formatar_percentual)
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.line_chart(df_tendencia.set_index("bloco")["taxa_revisao"])
