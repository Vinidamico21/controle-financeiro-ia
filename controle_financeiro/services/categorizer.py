import unicodedata


CATEGORIA_NAO_CLASSIFICADA = "Nao classificado"
CATEGORIA_OUTROS = "Outros"
TIPO_ENTRADA = "Entrada"
TIPO_SAIDA = "Saida"

CATEGORIAS_SAIDA = {
    "Combustivel": ["POSTO", "IPIRANGA", "SHELL", "BR MANIA"],
    "Supermercado": [
        "MARKET",
        "ATACADAO",
        "SUPERMERCADO",
        "CARREFOUR",
        "REAL DE EDEN SUPERMAR",
        "VYBE ATACADISTA",
    ],
    "Farmacia": ["DROGARIA", "FARMACIA", "RAIA", "DROGASIL"],
    "Condominio": [
        "CONDOMINIO",
        "CONDOMINIAL",
        "GARANTIA CONDOMINIAL",
        "DUPLIQUE ATLANTICA",
    ],
    "Moradia": ["CEG", "LIGHT", "ALUGUEL", "HABITACAO"],
    "Restaurante": [
        "OUTBACK",
        "TEMPEROS",
        "GOURM",
        "RESTAURANTE",
        "REFUGIO PIRATAS",
    ],
    "Padaria/Lanches": [
        "PADARIA",
        "LANCHE",
        "LANCHONETE",
        "CONVENIENCIA",
        "LEOLANCHE",
    ],
    "Lazer": ["BAR", "QUIOSQUE", "CINEMA"],
    "Transporte": ["UBER", "99APP", "METRO"],
    "Pedagio": ["PEDAGIO", "VIA DUTRA", "VIA LAGOS", "AUTO PISTA", "P7 ", "P6 "],
    "Beleza": ["SALAO", "BARBEARIA", "CABELEIREIRO", "MANICURE"],
    "Internet": ["INTERNET", "BANDA LARGA", "FIBRA", "REDE BRASIL"],
    "Estacionamento": [
        "ESTACIONAMENTO",
        "GRPARKING",
        "GR PARKING",
        "PARK",
        "PARKING",
        "ZONA AZUL",
        "ROTATIVO",
        "PARQUIMETRO",
        "WPS*ESTACIONAMENTO",
    ],
    "Seguro veiculo": [
        "FACILITY",
        "SEGURO",
        "SEGURADORA",
        "PROTECAO VEICULAR",
        "ASSOCIACAO VEICULAR",
    ],
    "Saude": ["HOSPITAL", "CLINICA", "LABORATORIO"],
    "Educacao": ["CURSO", "FACULDADE", "ESCOLA"],
    "Tributos": ["DETRAN", "IPVA", "DARF", "PREFEITURA", "MUNICIPIO"],
    "Cartao": ["FATURA", "CARTAO"],
    "Transferencia enviada": ["PIX", "TRANSFERENCIA ENVIADA"],
    "Investimentos": [
        "B3",
        "BOLSA",
        "CORRETORA",
        "CLEAR",
        "XP INVESTIMENTOS",
        "RICO",
        "NU INVEST",
        "INTER INVEST",
        "BTG",
        "APORTE",
        "APLICACAO RDB",
        "RDB",
        "COMPRA ACAO",
        "TESOURO DIRETO",
        "CDB",
        "FII",
    ],
    CATEGORIA_OUTROS: ["ESTORNO", "AJUSTE"],
}

CATEGORIAS_ENTRADA = {
    "Salario": ["SALARIO", "FOLHA", "PAGAMENTO EMPRESA"],
    "Transferencia recebida": [
        "TRANSFERENCIA RECEBIDA",
        "PIX RECEBIDO",
        "CREDITO EM CONTA",
        "TED RECEBIDA",
        "DOC RECEBIDO",
    ],
    "Reembolso": ["REEMBOLSO", "ESTORNO", "DEVOLUCAO", "RESSARCIMENTO"],
    "Rendimentos": ["RENDIMENTO", "JUROS", "BONUS"],
    "Venda": ["VENDA", "RECEBIMENTO", "CLIENTE"],
    "Investimentos": [
        "DIVIDENDO",
        "DIVIDENDOS",
        "JCP",
        "RENDIMENTO FII",
        "RESGATE",
        "VENDA ACAO",
        "TESOURO DIRETO",
        "CDB",
        "CORRETORA",
        "B3",
        "BOLSA",
    ],
    CATEGORIA_OUTROS: ["RENDIMENTO LIQUIDO", "ESTORNO", "AJUSTE"],
}


def normalizar_texto(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto_sem_acentos = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    return texto_sem_acentos.upper().strip()


def obter_categorias_por_tipo(tipo_movimentacao=None):
    if tipo_movimentacao == TIPO_ENTRADA:
        return CATEGORIAS_ENTRADA

    if tipo_movimentacao == TIPO_SAIDA:
        return CATEGORIAS_SAIDA

    return {**CATEGORIAS_SAIDA, **CATEGORIAS_ENTRADA}


def categorizar_por_regras(descricao, tipo_movimentacao=None):
    descricao_normalizada = normalizar_texto(descricao)
    categorias_regras = obter_categorias_por_tipo(tipo_movimentacao)

    for categoria, palavras in categorias_regras.items():
        for palavra in palavras:
            if palavra in descricao_normalizada:
                return categoria

    return CATEGORIA_NAO_CLASSIFICADA


def categorias_disponiveis(categorias_extras=None, tipo_movimentacao=None):
    categorias = list(obter_categorias_por_tipo(tipo_movimentacao).keys())

    if tipo_movimentacao is None:
        for categoria in list(CATEGORIAS_SAIDA.keys()) + list(CATEGORIAS_ENTRADA.keys()):
            if categoria not in categorias:
                categorias.append(categoria)

    if categorias_extras:
        for categoria in sorted(set(categorias_extras)):
            if categoria and categoria not in categorias:
                categorias.append(categoria)

    if CATEGORIA_NAO_CLASSIFICADA not in categorias:
        categorias.append(CATEGORIA_NAO_CLASSIFICADA)

    return categorias
