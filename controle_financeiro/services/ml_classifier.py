import pickle
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from database.system_store import carregar_artefato, remover_artefato, salvar_artefato
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from services.categorizer import CATEGORIA_NAO_CLASSIFICADA, normalizar_texto


CONFIANCA_MINIMA_PADRAO = 0.55
CONFIANCA_MINIMA_TIPO = 0.65
MINIMO_AMOSTRAS_TREINO = 8
CAMINHO_MODELO = Path(__file__).resolve().parent.parent / "data" / "modelo_ml.pkl"
CHAVE_ARTEFATO_MODELO = "modelo_ml_principal"


def criar_pipeline():
    return Pipeline(
        steps=[
            (
                "vetorizador",
                TfidfVectorizer(
                    preprocessor=normalizar_texto,
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                ),
            ),
            (
                "classificador",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def filtrar_amostras_categoria(base_treinamento):
    amostras = []

    for item in base_treinamento:
        descricao = (item.get("descricao") or "").strip()
        categoria = (item.get("categoria") or "").strip()

        if descricao and categoria and categoria != CATEGORIA_NAO_CLASSIFICADA:
            amostras.append({"descricao": descricao, "label": categoria})

    return amostras


def filtrar_amostras_tipo(base_treinamento):
    amostras = []

    for item in base_treinamento:
        descricao = (item.get("descricao") or "").strip()
        tipo_movimentacao = (item.get("tipo_movimentacao") or "").strip()

        if descricao and tipo_movimentacao:
            amostras.append({"descricao": descricao, "label": tipo_movimentacao})

    return amostras


def salvar_modelo(payload):
    salvar_artefato(
        CHAVE_ARTEFATO_MODELO,
        pickle.dumps(payload),
        metadata={"fonte": "pickle"},
    )

    CAMINHO_MODELO.parent.mkdir(parents=True, exist_ok=True)

    with CAMINHO_MODELO.open("wb") as arquivo_modelo:
        pickle.dump(payload, arquivo_modelo)


def carregar_modelo():
    artefato = carregar_artefato(CHAVE_ARTEFATO_MODELO)

    if artefato and artefato.get("payload"):
        return pickle.loads(artefato["payload"])

    if not CAMINHO_MODELO.exists():
        return None

    with CAMINHO_MODELO.open("rb") as arquivo_modelo:
        payload = pickle.load(arquivo_modelo)

    salvar_artefato(
        CHAVE_ARTEFATO_MODELO,
        pickle.dumps(payload),
        metadata={"fonte": "migrado_do_arquivo_local"},
    )
    return payload


def resetar_modelo():
    remover_artefato(CHAVE_ARTEFATO_MODELO)

    if CAMINHO_MODELO.exists():
        CAMINHO_MODELO.unlink()


def extrair_modelo(payload, nome_modelo):
    if not payload:
        return None

    if "modelos" in payload:
        return payload["modelos"].get(nome_modelo)

    if nome_modelo == "categoria" and "pipeline" in payload:
        return payload["pipeline"]

    return None


def obter_status_vazio():
    return {
        "modelo_disponivel": False,
        "total_amostras": 0,
        "total_categorias": 0,
        "categorias": [],
        "acuracia_validacao": None,
        "modelo_tipo_disponivel": False,
        "total_amostras_tipo": 0,
        "tipos": [],
        "acuracia_tipo": None,
        "treinado_em": None,
    }


def obter_status_modelo():
    payload = carregar_modelo()

    if not payload:
        return obter_status_vazio()

    metadata = payload.get("metadata", {}).copy()
    status = obter_status_vazio()
    status.update(metadata)
    status["modelo_disponivel"] = bool(extrair_modelo(payload, "categoria"))
    status["modelo_tipo_disponivel"] = bool(extrair_modelo(payload, "tipo"))
    return status


def calcular_acuracia(x, y):
    contagem_por_classe = Counter(y)
    total_classes = len(contagem_por_classe)
    total_amostras = len(x)

    if total_classes < 2:
        return None

    if min(contagem_por_classe.values()) < 2:
        return None

    if total_amostras < total_classes * 2:
        return None

    tamanho_teste = max(total_classes, int(round(total_amostras * 0.25)))
    tamanho_teste = min(tamanho_teste, total_amostras - total_classes)

    if tamanho_teste < total_classes:
        return None

    x_treino, x_teste, y_treino, y_teste = train_test_split(
        x,
        y,
        test_size=tamanho_teste,
        random_state=42,
        stratify=y,
    )

    pipeline = criar_pipeline()
    pipeline.fit(x_treino, y_treino)
    previsoes = pipeline.predict(x_teste)
    return float(accuracy_score(y_teste, previsoes))


def treinar_modelo(amostras):
    labels = sorted({amostra["label"] for amostra in amostras})

    if len(amostras) < MINIMO_AMOSTRAS_TREINO or len(labels) < 2:
        return None, labels, None

    x = [amostra["descricao"] for amostra in amostras]
    y = [amostra["label"] for amostra in amostras]

    acuracia = calcular_acuracia(x, y)
    pipeline = criar_pipeline()
    pipeline.fit(x, y)
    return pipeline, labels, acuracia


def treinar_e_salvar_modelo(base_treinamento):
    amostras_categoria = filtrar_amostras_categoria(base_treinamento)
    amostras_tipo = filtrar_amostras_tipo(base_treinamento)

    modelo_categoria, categorias, acuracia_categoria = treinar_modelo(
        amostras_categoria
    )
    modelo_tipo, tipos, acuracia_tipo = treinar_modelo(amostras_tipo)

    metadata = {
        "modelo_disponivel": bool(modelo_categoria),
        "total_amostras": len(amostras_categoria),
        "total_categorias": len(categorias),
        "categorias": categorias,
        "acuracia_validacao": acuracia_categoria,
        "modelo_tipo_disponivel": bool(modelo_tipo),
        "total_amostras_tipo": len(amostras_tipo),
        "tipos": tipos,
        "acuracia_tipo": acuracia_tipo,
        "treinado_em": datetime.now(timezone.utc).isoformat(),
    }

    if not modelo_categoria and not modelo_tipo:
        return metadata

    salvar_modelo(
        {
            "modelos": {
                "categoria": modelo_categoria,
                "tipo": modelo_tipo,
            },
            "metadata": metadata,
        }
    )
    return metadata


def prever_labels(descricoes, nome_modelo, confianca_minima=None):
    payload = carregar_modelo()
    pipeline = extrair_modelo(payload, nome_modelo)

    if not pipeline or not descricoes:
        return []

    probabilidades = pipeline.predict_proba(descricoes)
    labels = pipeline.classes_
    previsoes = []

    for indice, descricao in enumerate(descricoes):
        probabilidades_descricao = probabilidades[indice]
        indice_melhor_label = int(probabilidades_descricao.argmax())
        label = labels[indice_melhor_label]
        confianca = float(probabilidades_descricao[indice_melhor_label])

        if confianca_minima is not None and confianca < confianca_minima:
            label = None

        previsoes.append(
            {
                "descricao": descricao,
                "label": label,
                "confianca": confianca,
            }
        )

    return previsoes


def prever_categorias(descricoes):
    previsoes = prever_labels(
        descricoes,
        nome_modelo="categoria",
        confianca_minima=CONFIANCA_MINIMA_PADRAO,
    )
    resultado = []

    for previsao in previsoes:
        resultado.append(
            {
                "descricao": previsao["descricao"],
                "categoria": previsao["label"] or CATEGORIA_NAO_CLASSIFICADA,
                "confianca": previsao["confianca"],
            }
        )

    return resultado


def prever_tipos(descricoes):
    previsoes = prever_labels(
        descricoes,
        nome_modelo="tipo",
        confianca_minima=CONFIANCA_MINIMA_TIPO,
    )
    resultado = []

    for previsao in previsoes:
        resultado.append(
            {
                "descricao": previsao["descricao"],
                "tipo_movimentacao": previsao["label"],
                "confianca": previsao["confianca"],
            }
        )

    return resultado
