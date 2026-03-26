import pdfplumber

def extrair_texto_pdf(arquivo):
    texto = ""

    with pdfplumber.open(arquivo) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() + "\n"

    return texto