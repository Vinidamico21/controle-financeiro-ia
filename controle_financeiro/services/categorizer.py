import unicodedata


CATEGORIA_NAO_CLASSIFICADA = "Nao classificado"

CATEGORIAS = {
    "Combustivel": ["POSTO", "IPIRANGA", "SHELL", "BR MANIA"],
    "Supermercado": ["MARKET", "ATACADAO", "SUPERMERCADO", "CARREFOUR"],
    "Farmacia": ["DROGARIA", "FARMACIA", "RAIA", "DROGASIL"],
    "Moradia": ["CEG", "LIGHT", "ALUGUEL", "CONDOMINIO", "HABITACAO"],
    "Lazer": ["BAR", "QUIOSQUE", "CINEMA", "RESTAURANTE"],
    "Transporte": ["UBER", "99APP", "METRO", "PEDAGIO"],
    "Saude": ["HOSPITAL", "CLINICA", "LABORATORIO"],
    "Educacao": ["CURSO", "FACULDADE", "ESCOLA"],
}


def normalizar_texto(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto_sem_acentos = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    return texto_sem_acentos.upper().strip()


def categorizar_por_regras(descricao):
    descricao_normalizada = normalizar_texto(descricao)

    for categoria, palavras in CATEGORIAS.items():
        for palavra in palavras:
            if palavra in descricao_normalizada:
                return categoria

    return CATEGORIA_NAO_CLASSIFICADA


def categorias_disponiveis(categorias_extras=None):
    categorias = list(CATEGORIAS.keys())

    if categorias_extras:
        for categoria in sorted(set(categorias_extras)):
            if categoria and categoria not in categorias:
                categorias.append(categoria)

    if CATEGORIA_NAO_CLASSIFICADA not in categorias:
        categorias.append(CATEGORIA_NAO_CLASSIFICADA)

    return categorias
