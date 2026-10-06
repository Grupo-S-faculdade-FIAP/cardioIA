"""Contrato do dataset de risco (SDD Fase 2, §4)."""

import hashlib
from pathlib import Path

import pandas as pd

from extrator_sintomas import normalizar_texto

RAIZ_FASE2 = Path(__file__).resolve().parent.parent
ARQUIVO_DATASET = RAIZ_FASE2 / "data" / "frases_risco.csv"
ARQUIVO_TESTE_CONGELADO = RAIZ_FASE2 / "config" / "teste_congelado.json"

COLUNAS = ["frase", "situacao", "origem", "particao", "criterio"]
ROTULOS = {"alto risco", "baixo risco"}
ORIGENS = {"manual", "template"}
PARTICOES = {"treino", "teste"}
CRITERIOS = {"A1": "alto risco", "A2": "alto risco", "A3": "alto risco", "A4": "alto risco",
             "B1": "baixo risco", "B2": "baixo risco", "B3": "baixo risco"}


def carregar_dataset_risco(caminho=ARQUIVO_DATASET):
    return pd.read_csv(caminho, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def hash_conjunto_teste(df):
    """SHA-256 das linhas de teste (frase, situação, critério), na ordem do arquivo."""
    teste = df[df["particao"] == "teste"][["frase", "situacao", "criterio"]]
    conteudo = "\n".join("\t".join(linha) for linha in teste.itertuples(index=False))
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def _checar_proporcao(df, nome, proporcao_minima, erros):
    if df.empty:
        return
    proporcoes = df["situacao"].value_counts(normalize=True)
    for rotulo in sorted(ROTULOS):
        if proporcoes.get(rotulo, 0.0) < proporcao_minima:
            erros.append(
                f"{nome}: classe '{rotulo}' com {proporcoes.get(rotulo, 0.0):.0%} "
                f"(mínimo {proporcao_minima:.0%})"
            )


def validar_dataset_risco(df, tamanho_minimo=200, teste_minimo=40, proporcao_minima=0.35):
    """Devolve a lista de violações do contrato; lista vazia = dataset válido."""
    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        return [f"colunas ausentes: {faltando}"]

    erros = []

    for coluna, permitidos in (
        ("situacao", ROTULOS), ("origem", ORIGENS), ("particao", PARTICOES), ("criterio", set(CRITERIOS)),
    ):
        invalidos = sorted(set(df[coluna]) - permitidos)
        if invalidos:
            erros.append(f"'{coluna}' com valores fora do contrato: {invalidos}")

    incoerentes = df.index[df["criterio"].map(CRITERIOS).fillna(df["situacao"]) != df["situacao"]].tolist()
    if incoerentes:
        erros.append(f"critério incoerente com a situação nas linhas {incoerentes}")

    vazias = df.index[df["frase"].str.strip() == ""].tolist()
    if vazias:
        erros.append(f"frases vazias nas linhas {vazias}")

    teste = df[df["particao"] == "teste"]
    template_no_teste = teste.index[teste["origem"] != "manual"].tolist()
    if template_no_teste:
        erros.append(f"teste deve ter só frases manuais; linhas {template_no_teste}")

    normalizadas = df["frase"].map(normalizar_texto)
    duplicadas = df[normalizadas.duplicated(keep=False)]
    if not duplicadas.empty:
        erros.append(f"frases duplicadas após normalização: {duplicadas['frase'].tolist()}")

    if len(df) < tamanho_minimo:
        erros.append(f"{len(df)} frases (mínimo {tamanho_minimo})")
    if len(teste) < teste_minimo:
        erros.append(f"{len(teste)} frases de teste (mínimo {teste_minimo})")

    _checar_proporcao(df, "arquivo", proporcao_minima, erros)
    _checar_proporcao(teste, "teste", proporcao_minima, erros)

    return erros
