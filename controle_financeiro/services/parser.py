import re
from datetime import date

from services.categorizer import normalizar_texto


TIPO_ENTRADA = "Entrada"
TIPO_SAIDA = "Saida"

PADRAO_VALOR = re.compile(r"([+-]?\d{1,3}(?:\.\d{3})*,\d{2}|[+-]?\d+,\d{2})")
PADRAO_DATA = re.compile(r"^(\d{2})\s+([A-Z]{3})\s+(\d{4})\s+TOTAL DE")

MAPA_MESES = {
    "JAN": 1,
    "FEV": 2,
    "MAR": 3,
    "ABR": 4,
    "MAI": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SET": 9,
    "OUT": 10,
    "NOV": 11,
    "DEZ": 12,
}

PADROES_DESPESA = [
    "COMPRA",
    "PAGAMENTO",
    "PIX ENVIADO",
    "DEBITO",
    "TRANSFERENCIA ENVIADA",
    "PAGAMENTO DE FATURA",
    "PAGAMENTO DE BOLETO",
    "APLICACAO RDB",
]

PADROES_RECEITA = [
    "SALARIO",
    "PIX RECEBIDO",
    "TRANSFERENCIA RECEBIDA",
    "RENDIMENTO LIQUIDO",
    "CREDITO",
]


def tipos_movimentacao_disponiveis():
    return [TIPO_ENTRADA, TIPO_SAIDA]


def extrair_valor(linha):
    valores = PADRAO_VALOR.findall(linha)

    if not valores:
        return None

    valor_texto = valores[-1].replace(".", "").replace(",", ".")
    return float(valor_texto)


def identificar_tipo_movimentacao(linha_normalizada):
    if any(padrao in linha_normalizada for padrao in PADROES_RECEITA):
        return TIPO_ENTRADA

    if any(padrao in linha_normalizada for padrao in PADROES_DESPESA):
        return TIPO_SAIDA

    return None


def extrair_data_cabecalho(linha_normalizada):
    correspondencia = PADRAO_DATA.match(linha_normalizada)

    if not correspondencia:
        return None

    dia = int(correspondencia.group(1))
    mes_abreviado = correspondencia.group(2)
    ano = int(correspondencia.group(3))
    mes = MAPA_MESES.get(mes_abreviado)

    if not mes:
        return None

    return date(ano, mes, dia).isoformat()


def aplicar_tipo_ao_valor(tipo_movimentacao, valor_absoluto):
    valor_absoluto = abs(float(valor_absoluto))

    if tipo_movimentacao == TIPO_ENTRADA:
        return valor_absoluto

    return -valor_absoluto


def extrair_transacoes(texto):
    transacoes = []
    data_atual = None

    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue

        linha_normalizada = normalizar_texto(linha)
        data_cabecalho = extrair_data_cabecalho(linha_normalizada)

        if data_cabecalho:
            data_atual = data_cabecalho
            continue

        valor_absoluto = extrair_valor(linha)

        if valor_absoluto is None:
            continue

        if round(abs(valor_absoluto), 2) == 0:
            continue

        tipo_movimentacao = identificar_tipo_movimentacao(linha_normalizada)

        if not tipo_movimentacao:
            continue

        valor = aplicar_tipo_ao_valor(tipo_movimentacao, valor_absoluto)

        transacoes.append(
            {
                "data": data_atual,
                "descricao": linha,
                "valor": valor,
                "valor_original": valor,
                "tipo_movimentacao": tipo_movimentacao,
                "tipo_previsto": tipo_movimentacao,
                "tipo_origem": "REGRA_EXTRATO",
            }
        )

    return transacoes
