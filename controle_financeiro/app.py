import pandas as pd
import streamlit as st

from database.db import conectar
from database.models import criar_tabela
from database.repository import (
    buscar_base_treinamento,
    buscar_transacoes,
    salvar_transacoes,
)
from reports.report import gerar_resumo
from services.categorizer import (
    CATEGORIA_NAO_CLASSIFICADA,
    categorias_disponiveis,
    categorizar_por_regras,
)
from services.ml_classifier import (
    CONFIANCA_MINIMA_PADRAO,
    CONFIANCA_MINIMA_TIPO,
    obter_status_modelo,
    prever_categorias,
    prever_tipos,
    treinar_e_salvar_modelo,
)
from services.parser import (
    TIPO_ENTRADA,
    aplicar_tipo_ao_valor,
    extrair_transacoes,
    tipos_movimentacao_disponiveis,
)
from services.pdf_reader import extrair_texto_pdf


st.set_page_config(page_title="Controle Financeiro IA", layout="wide")

conn = conectar()
criar_tabela(conn)


def formatar_moeda(valor):
    if valor is None or pd.isna(valor):
        return "-"

    sinal = "-" if float(valor) < 0 else ""
    valor_formatado = f"{abs(float(valor)):,.2f}".replace(",", "X").replace(".", ",")
    valor_formatado = valor_formatado.replace("X", ".")
    return f"{sinal}R$ {valor_formatado}"


def formatar_confianca(valor):
    if valor is None or pd.isna(valor):
        return "-"

    return f"{float(valor):.0%}"


def carregar_status_modelo(force_retrain=False):
    base_treinamento = buscar_base_treinamento(conn)
    status_modelo = obter_status_modelo()

    deve_retreinar = (
        force_retrain
        or (
            not status_modelo.get("modelo_disponivel")
            and not status_modelo.get("modelo_tipo_disponivel")
            and len(base_treinamento) >= 8
        )
    )

    if deve_retreinar:
        status_modelo = treinar_e_salvar_modelo(base_treinamento)

    return status_modelo, base_treinamento


def construir_alertas(
    categoria,
    origem_categoria,
    confianca_categoria,
    tipo_movimentacao,
    tipo_ml,
    confianca_tipo,
    valor_original,
    valor_final,
):
    alertas = []

    if categoria == CATEGORIA_NAO_CLASSIFICADA:
        alertas.append("Categoria pendente de revisao")
    elif origem_categoria != "ML" or (
        confianca_categoria is not None and confianca_categoria < CONFIANCA_MINIMA_PADRAO
    ):
        alertas.append("Categoria sem alta confianca")

    if (
        tipo_ml
        and tipo_ml != tipo_movimentacao
        and confianca_tipo is not None
        and confianca_tipo >= CONFIANCA_MINIMA_TIPO
    ):
        alertas.append("Entrada/Saida divergente da IA")

    if round(abs(float(valor_final)), 2) != round(abs(float(valor_original)), 2):
        alertas.append("Valor ajustado manualmente")

    return " | ".join(alertas) if alertas else "Sem alertas"


def classificar_transacoes(transacoes):
    descricoes = [transacao["descricao"] for transacao in transacoes]
    previsoes_categoria = prever_categorias(descricoes)
    previsoes_tipo = prever_tipos(descricoes)
    transacoes_classificadas = []

    for indice, transacao in enumerate(transacoes):
        previsao_categoria = previsoes_categoria[indice] if previsoes_categoria else None
        previsao_tipo = previsoes_tipo[indice] if previsoes_tipo else None
        categoria_regra = categorizar_por_regras(transacao["descricao"])

        categoria = CATEGORIA_NAO_CLASSIFICADA
        categoria_prevista = CATEGORIA_NAO_CLASSIFICADA
        origem = "PENDENTE"
        confianca = None

        if previsao_categoria and previsao_categoria["categoria"] != CATEGORIA_NAO_CLASSIFICADA:
            categoria = previsao_categoria["categoria"]
            categoria_prevista = previsao_categoria["categoria"]
            origem = "ML"
            confianca = previsao_categoria["confianca"]

        if (
            categoria_regra != CATEGORIA_NAO_CLASSIFICADA
            and (confianca is None or confianca < CONFIANCA_MINIMA_PADRAO)
        ):
            categoria = categoria_regra
            categoria_prevista = categoria_regra
            origem = "REGRA"

        if categoria == CATEGORIA_NAO_CLASSIFICADA and previsao_categoria:
            confianca = previsao_categoria["confianca"]

        tipo_movimentacao = transacao.get("tipo_movimentacao")
        tipo_ml = previsao_tipo["tipo_movimentacao"] if previsao_tipo else None
        confianca_tipo = previsao_tipo["confianca"] if previsao_tipo else None

        if not tipo_movimentacao and tipo_ml:
            tipo_movimentacao = tipo_ml

        if not tipo_movimentacao:
            tipo_movimentacao = "Saida"

        alerta_revisao = construir_alertas(
            categoria=categoria,
            origem_categoria=origem,
            confianca_categoria=confianca,
            tipo_movimentacao=tipo_movimentacao,
            tipo_ml=tipo_ml,
            confianca_tipo=confianca_tipo,
            valor_original=transacao["valor_original"],
            valor_final=transacao["valor"],
        )

        precisa_revisao = alerta_revisao != "Sem alertas"

        transacoes_classificadas.append(
            {
                **transacao,
                "categoria": categoria,
                "categoria_prevista": categoria_prevista,
                "origem": origem,
                "confianca": confianca,
                "tipo_movimentacao": tipo_movimentacao,
                "tipo_previsto": tipo_movimentacao,
                "tipo_previsto_ml": tipo_ml,
                "confianca_tipo": confianca_tipo,
                "alerta_revisao": alerta_revisao,
                "precisa_revisao": precisa_revisao,
            }
        )

    return pd.DataFrame(transacoes_classificadas)


def exibir_sidebar(status_modelo):
    st.sidebar.header("Motor de IA")

    if status_modelo.get("modelo_disponivel"):
        st.sidebar.success("Modelo de categoria treinado.")
    else:
        st.sidebar.warning("Modelo de categoria ainda sem dados suficientes.")

    st.sidebar.metric("Amostras de categoria", status_modelo.get("total_amostras", 0))
    st.sidebar.metric("Categorias conhecidas", status_modelo.get("total_categorias", 0))

    acuracia_categoria = status_modelo.get("acuracia_validacao")
    if acuracia_categoria is not None:
        st.sidebar.metric("Acuracia de categoria", f"{acuracia_categoria:.1%}")

    st.sidebar.divider()

    if status_modelo.get("modelo_tipo_disponivel"):
        st.sidebar.success("Modelo de Entrada/Saida treinado.")
    else:
        st.sidebar.info("Modelo de Entrada/Saida aprendendo com suas revisoes.")

    st.sidebar.metric(
        "Amostras de Entrada/Saida",
        status_modelo.get("total_amostras_tipo", 0),
    )

    acuracia_tipo = status_modelo.get("acuracia_tipo")
    if acuracia_tipo is not None:
        st.sidebar.metric("Acuracia de tipo", f"{acuracia_tipo:.1%}")

    categorias = status_modelo.get("categorias", [])
    if categorias:
        st.sidebar.caption("Categorias aprendidas: " + ", ".join(categorias))

    tipos = status_modelo.get("tipos", [])
    if tipos:
        st.sidebar.caption("Tipos aprendidos: " + ", ".join(tipos))


def aplicar_estilo_preview(df_preview):
    formatos = {}

    if "valor_original" in df_preview.columns:
        formatos["valor_original"] = formatar_moeda

    if "valor_corrigido" in df_preview.columns:
        formatos["valor_corrigido"] = formatar_moeda

    estilo = df_preview.style.format(formatos)

    if "tipo_movimentacao" in df_preview.columns:
        estilo = estilo.map(
            lambda valor: "color: #0f9d58; font-weight: 700"
            if valor == TIPO_ENTRADA
            else "color: #c5221f; font-weight: 700",
            subset=["tipo_movimentacao"],
        )

    if "valor_corrigido" in df_preview.columns:
        estilo = estilo.map(
            lambda valor: "color: #0f9d58; font-weight: 700"
            if float(valor) >= 0
            else "color: #c5221f; font-weight: 700",
            subset=["valor_corrigido"],
        )

    return estilo


def exibir_metricas_fluxo(df_transacoes):
    entradas = df_transacoes[df_transacoes["valor"] > 0]["valor"].sum()
    saidas = df_transacoes[df_transacoes["valor"] < 0]["valor"].sum()
    saldo = entradas + saidas
    revisoes = int(df_transacoes["precisa_revisao"].sum())

    coluna1, coluna2, coluna3, coluna4 = st.columns(4)
    coluna1.metric("Entradas", formatar_moeda(entradas))
    coluna2.metric("Saidas", formatar_moeda(saidas))
    coluna3.metric("Saldo", formatar_moeda(saldo))
    coluna4.metric("Itens para revisar", revisoes)


status_modelo, base_treinamento = carregar_status_modelo()

if "mensagem_sucesso" in st.session_state:
    st.success(st.session_state.pop("mensagem_sucesso"))

st.title("Controle Financeiro Inteligente com Machine Learning")
st.caption(
    "Agora voce pode revisar categoria, Entrada/Saida e valor antes de salvar. "
    "Cada ajuste ajuda a IA a aprender melhor com o seu historico real."
)

exibir_sidebar(status_modelo)

if st.sidebar.button("Retreinar modelo com historico"):
    status_modelo, base_treinamento = carregar_status_modelo(force_retrain=True)
    st.sidebar.success("Modelo atualizado com o historico mais recente.")

arquivo = st.file_uploader("Envie seu extrato PDF", type="pdf")

if arquivo:
    texto = extrair_texto_pdf(arquivo)
    transacoes = extrair_transacoes(texto)

    if not transacoes:
        st.warning("Nenhuma transacao foi identificada no PDF enviado.")
    else:
        df_classificado = classificar_transacoes(transacoes)
        categorias_historicas = [item["categoria"] for item in base_treinamento]
        opcoes_categoria = categorias_disponiveis(categorias_historicas)

        exibir_metricas_fluxo(df_classificado)

        st.subheader("Revisao inteligente das transacoes")
        st.caption(
            "Edite a categoria, o tipo de movimentacao e o valor quando necessario. "
            "O valor deve ser informado sempre como magnitude positiva, e o sistema "
            "aplica o sinal com base em Entrada ou Saida."
        )

        df_editor = df_classificado[
            [
                "descricao",
                "tipo_movimentacao",
                "categoria",
                "origem",
                "confianca",
                "confianca_tipo",
                "alerta_revisao",
            ]
        ].copy()
        df_editor["valor_editavel"] = df_classificado["valor"].abs()

        df_editor = df_editor[
            [
                "descricao",
                "tipo_movimentacao",
                "valor_editavel",
                "categoria",
                "origem",
                "confianca",
                "confianca_tipo",
                "alerta_revisao",
            ]
        ]

        df_editado = st.data_editor(
            df_editor,
            hide_index=True,
            use_container_width=True,
            column_config={
                "descricao": st.column_config.TextColumn("Descricao", width="large"),
                "tipo_movimentacao": st.column_config.SelectboxColumn(
                    "Tipo",
                    options=tipos_movimentacao_disponiveis(),
                    required=True,
                ),
                "valor_editavel": st.column_config.NumberColumn(
                    "Valor (R$)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    required=True,
                ),
                "categoria": st.column_config.SelectboxColumn(
                    "Categoria",
                    options=opcoes_categoria,
                    required=True,
                ),
                "origem": st.column_config.TextColumn("Origem categoria"),
                "confianca": st.column_config.NumberColumn(
                    "Confianca categoria",
                    format="%.2f",
                ),
                "confianca_tipo": st.column_config.NumberColumn(
                    "Confianca tipo",
                    format="%.2f",
                ),
                "alerta_revisao": st.column_config.TextColumn(
                    "Alertas",
                    width="large",
                ),
            },
            disabled=["descricao", "origem", "confianca", "confianca_tipo", "alerta_revisao"],
        )

        df_para_salvar = df_classificado.copy()
        df_para_salvar["categoria"] = df_editado["categoria"].values
        df_para_salvar["tipo_movimentacao"] = df_editado["tipo_movimentacao"].values
        df_para_salvar["valor_corrigido"] = [
            aplicar_tipo_ao_valor(tipo, valor)
            for tipo, valor in zip(
                df_editado["tipo_movimentacao"].values,
                df_editado["valor_editavel"].fillna(0).values,
            )
        ]
        df_para_salvar["valor"] = df_para_salvar["valor_corrigido"]
        df_para_salvar["alerta_revisao"] = [
            construir_alertas(
                categoria=categoria,
                origem_categoria=origem,
                confianca_categoria=confianca_categoria,
                tipo_movimentacao=tipo_movimentacao,
                tipo_ml=tipo_ml,
                confianca_tipo=confianca_tipo,
                valor_original=valor_original,
                valor_final=valor_final,
            )
            for categoria, origem, confianca_categoria, tipo_movimentacao, tipo_ml, confianca_tipo, valor_original, valor_final in zip(
                df_para_salvar["categoria"].values,
                df_para_salvar["origem"].values,
                df_para_salvar["confianca"].values,
                df_para_salvar["tipo_movimentacao"].values,
                df_para_salvar["tipo_previsto_ml"].values,
                df_para_salvar["confianca_tipo"].values,
                df_para_salvar["valor_original"].values,
                df_para_salvar["valor_corrigido"].values,
            )
        ]
        df_para_salvar["precisa_revisao"] = (
            df_para_salvar["alerta_revisao"] != "Sem alertas"
        )

        ajustes_manuais = (
            (df_para_salvar["categoria"] != df_classificado["categoria"])
            | (
                df_para_salvar["tipo_movimentacao"]
                != df_classificado["tipo_movimentacao"]
            )
            | (
                df_para_salvar["valor_corrigido"].round(2)
                != df_classificado["valor_original"].round(2)
            )
        )

        st.subheader("Preview final antes de salvar")
        st.caption(
            f"{int(ajustes_manuais.sum())} transacao(oes) com ajuste manual nesta carga."
        )

        df_preview = df_para_salvar[
            [
                "descricao",
                "tipo_movimentacao",
                "valor_original",
                "valor_corrigido",
                "categoria",
                "alerta_revisao",
            ]
        ].copy()
        st.dataframe(
            aplicar_estilo_preview(df_preview),
            hide_index=True,
            use_container_width=True,
        )

        pendentes = df_para_salvar[df_para_salvar["precisa_revisao"]][
            ["descricao", "tipo_movimentacao", "categoria", "alerta_revisao"]
        ]

        st.subheader("Itens que merecem atencao")
        if pendentes.empty:
            st.success("Nenhuma transacao precisa de revisao manual nesta carga.")
        else:
            st.dataframe(pendentes, hide_index=True, use_container_width=True)

        resumo = gerar_resumo(df_para_salvar[["categoria", "valor"]])
        st.subheader("Resumo financeiro")
        st.dataframe(resumo, hide_index=True, use_container_width=True)

        if not resumo.empty:
            st.bar_chart(resumo.set_index("categoria")["valor"])

        if st.button("Salvar transacoes e re-treinar IA", type="primary"):
            salvar_transacoes(conn, df_para_salvar.to_dict("records"))
            status_modelo = treinar_e_salvar_modelo(buscar_base_treinamento(conn))
            st.session_state["mensagem_sucesso"] = (
                "Transacoes salvas. A IA agora aprende com categoria, Entrada/Saida "
                "e com os valores que voce corrigiu nesta revisao."
            )
            st.rerun()

st.subheader("Historico salvo")
historico = buscar_transacoes(conn)

if historico:
    df_historico = pd.DataFrame(historico)
    df_historico_exibicao = df_historico[
        [
            "descricao",
            "tipo_movimentacao",
            "valor_corrigido",
            "categoria",
            "status",
            "revisado_usuario",
            "alerta_revisao",
        ]
    ].copy()
    st.dataframe(
        aplicar_estilo_preview(df_historico_exibicao),
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("Ainda nao ha transacoes salvas no banco.")
