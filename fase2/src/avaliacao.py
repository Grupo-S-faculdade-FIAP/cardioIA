"""Harness de avaliação do classificador de risco (SDD Fase 2, §5 e §6).

Uso:
    python fase2/src/avaliacao.py --modelo todos
Sai com código 1 se o dataset violar o contrato ou se as metas não forem cumpridas.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    make_scorer,
    precision_recall_fscore_support,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from contrato_dataset import ARQUIVO_DATASET, carregar_dataset_risco, validar_dataset_risco
from extrator_sintomas import normalizar_texto

RAIZ_FASE2 = Path(__file__).resolve().parent.parent
ARQUIVO_CASOS = RAIZ_FASE2 / "data" / "casos_comportamento.csv"
ARQUIVO_METAS = RAIZ_FASE2 / "config" / "metas_avaliacao.json"
PASTA_RELATORIOS = RAIZ_FASE2 / "reports"

SEED = 42
POSITIVO = "alto risco"
NEGATIVO = "baixo risco"


def _vetorizador():
    return TfidfVectorizer(preprocessor=normalizar_texto, ngram_range=(1, 2))


def criar_modelos():
    return {
        "logreg": Pipeline([
            ("tfidf", _vetorizador()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED)),
        ]),
        "arvore": Pipeline([
            ("tfidf", _vetorizador()),
            ("clf", DecisionTreeClassifier(class_weight="balanced", random_state=SEED)),
        ]),
        "naive_bayes": Pipeline([
            ("tfidf", _vetorizador()),
            ("clf", MultinomialNB()),
        ]),
    }


def calcular_metricas(y_true, y_pred):
    precisao, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=[POSITIVO], zero_division=0
    )
    return {
        "n": len(y_true),
        "acuracia": float(accuracy_score(y_true, y_pred)),
        "precisao_alto_risco": float(precisao[0]),
        "recall_alto_risco": float(recall[0]),
        "f1_alto_risco": float(f1[0]),
        "matriz_confusao": {
            "rotulos": [NEGATIVO, POSITIVO],
            "valores": confusion_matrix(y_true, y_pred, labels=[NEGATIVO, POSITIVO]).tolist(),
        },
    }


def validacao_cruzada(modelo, frases, rotulos, k=5):
    resultado = cross_validate(
        modelo,
        frases,
        rotulos,
        cv=StratifiedKFold(n_splits=k, shuffle=True, random_state=SEED),
        scoring={
            "acuracia": "accuracy",
            "recall_alto_risco": make_scorer(recall_score, pos_label=POSITIVO, zero_division=0),
        },
    )
    return {
        nome: {
            "media": float(resultado[f"test_{nome}"].mean()),
            "desvio": float(resultado[f"test_{nome}"].std()),
        }
        for nome in ("acuracia", "recall_alto_risco")
    }


def avaliar_comportamento(modelo, casos):
    """Casos de §6: relatados por tipo, não usados como meta."""
    previstos = modelo.predict(casos["frase"])
    por_tipo = {}
    falhas = []

    for (_, caso), previsto in zip(casos.iterrows(), previstos):
        grupo = por_tipo.setdefault(caso["tipo"], {"acertos": 0, "total": 0})
        grupo["total"] += 1
        if previsto == caso["risco_esperado"]:
            grupo["acertos"] += 1
        else:
            falhas.append({
                "caso_id": caso["caso_id"],
                "tipo": caso["tipo"],
                "frase": caso["frase"],
                "esperado": caso["risco_esperado"],
                "previsto": previsto,
            })

    for grupo in por_tipo.values():
        grupo["taxa_acerto"] = grupo["acertos"] / grupo["total"]

    return {"por_tipo": por_tipo, "falhas": falhas}


def verificar_metas(metricas, metas):
    return [
        f"{nome} = {metricas[nome]:.3f} < meta {minimo:.2f}"
        for nome, minimo in metas.items()
        if metricas[nome] < minimo
    ]


def _sha256(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def executar(nome_modelo="todos", caminho_dataset=ARQUIVO_DATASET, caminho_casos=ARQUIVO_CASOS,
             caminho_metas=ARQUIVO_METAS, pasta_saida=PASTA_RELATORIOS, k=5, validar_contrato=True):
    """Treina, avalia e grava o relatório JSON. Devolve o relatório."""
    df = carregar_dataset_risco(caminho_dataset)
    if validar_contrato:
        erros = validar_dataset_risco(df)
        if erros:
            raise ValueError("dataset viola o contrato (SDD §4):\n- " + "\n- ".join(erros))

    treino = df[df["particao"] == "treino"]
    teste = df[df["particao"] == "teste"]
    modelos = criar_modelos()

    candidatos = list(modelos) if nome_modelo == "todos" else [nome_modelo]
    cv = {nome: validacao_cruzada(modelos[nome], treino["frase"], treino["situacao"], k) for nome in candidatos}

    # Seleção só pela validação cruzada no treino: o teste não escolhe modelo (SDD §4).
    escolhido = max(
        candidatos,
        key=lambda nome: (cv[nome]["recall_alto_risco"]["media"], cv[nome]["acuracia"]["media"]),
    )
    modelo = modelos[escolhido].fit(treino["frase"], treino["situacao"])
    metricas_teste = calcular_metricas(teste["situacao"].tolist(), modelo.predict(teste["frase"]).tolist())
    metas = json.loads(Path(caminho_metas).read_text(encoding="utf-8"))

    relatorio = {
        "modelo_escolhido": escolhido,
        "seed": SEED,
        "dataset": {
            "arquivo": Path(caminho_dataset).name,
            "sha256": _sha256(caminho_dataset),
            "n_treino": len(treino),
            "n_teste": len(teste),
        },
        "validacao_cruzada": cv,
        "teste": metricas_teste,
        "metas": metas,
        "violacoes": verificar_metas(metricas_teste, metas),
    }

    if Path(caminho_casos).exists():
        casos = pd.read_csv(caminho_casos, encoding="utf-8-sig", dtype=str)
        relatorio["comportamento"] = avaliar_comportamento(modelo, casos)

    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    (pasta_saida / f"metricas_{nome_modelo}.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return relatorio


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", default="todos", choices=["todos", *criar_modelos()])
    parser.add_argument("--dataset", default=ARQUIVO_DATASET, type=Path)
    args = parser.parse_args()

    try:
        relatorio = executar(args.modelo, args.dataset)
    except (FileNotFoundError, ValueError) as erro:
        print(f"ERRO: {erro}")
        return 1

    teste = relatorio["teste"]
    print(f"Modelo escolhido (validação cruzada): {relatorio['modelo_escolhido']}")
    print(f"Teste manual (n={teste['n']}): acurácia {teste['acuracia']:.3f} | "
          f"recall alto risco {teste['recall_alto_risco']:.3f} | "
          f"precisão alto risco {teste['precisao_alto_risco']:.3f}")
    for tipo, grupo in relatorio.get("comportamento", {}).get("por_tipo", {}).items():
        print(f"  comportamento/{tipo}: {grupo['acertos']}/{grupo['total']}")

    if relatorio["violacoes"]:
        print("METAS NÃO CUMPRIDAS:\n- " + "\n- ".join(relatorio["violacoes"]))
        return 1
    print("Metas cumpridas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
