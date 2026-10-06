"""Harness de avaliação (SDD Fase 2, §5 / R8)."""

import json

import pytest

from avaliacao import (
    ARQUIVO_CASOS,
    calcular_metricas,
    criar_modelos,
    executar,
    verificar_metas,
)
from contrato_dataset import ARQUIVO_DATASET

A, B = "alto risco", "baixo risco"


def test_calcular_metricas_valores_conhecidos():
    m = calcular_metricas([A, A, B, B], [A, B, B, B])
    assert m["acuracia"] == 0.75
    assert m["recall_alto_risco"] == 0.5
    assert m["precisao_alto_risco"] == 1.0
    assert m["matriz_confusao"]["valores"] == [[2, 0], [1, 1]]


def test_verificar_metas():
    assert verificar_metas({"recall_alto_risco": 0.95, "acuracia": 0.7}, {"recall_alto_risco": 0.9, "acuracia": 0.8}) == [
        "acuracia = 0.700 < meta 0.80"
    ]


@pytest.mark.parametrize("nome", sorted(criar_modelos()))
def test_modelos_treinam_e_preveem(nome, dataset_sintetico):
    modelo = criar_modelos()[nome].fit(dataset_sintetico["frase"], dataset_sintetico["situacao"])
    assert set(modelo.predict(["dor forte no peito", "leve incômodo"])) <= {A, B}


def test_executar_ponta_a_ponta(caminho_dataset_sintetico, tmp_path):
    relatorio = executar("todos", caminho_dataset_sintetico, ARQUIVO_CASOS, pasta_saida=tmp_path)
    gravado = json.loads((tmp_path / "metricas_todos.json").read_text(encoding="utf-8"))

    assert gravado == relatorio
    assert relatorio["modelo_escolhido"] in criar_modelos()
    assert relatorio["dataset"]["n_teste"] == 48
    assert relatorio["violacoes"] == []
    assert set(relatorio["comportamento"]["por_tipo"]) == {"negacao", "genero", "acento", "coloquial", "atipico"}


def test_executar_recusa_dataset_fora_do_contrato(dataset_sintetico, tmp_path):
    caminho = tmp_path / "invalido.csv"
    dataset_sintetico.assign(origem="template").to_csv(caminho, index=False)
    with pytest.raises(ValueError, match="viola o contrato"):
        executar("logreg", caminho, ARQUIVO_CASOS, pasta_saida=tmp_path)


@pytest.mark.skipif(not ARQUIVO_DATASET.exists(), reason="frases_risco.csv ainda não criado")
def test_metas_dataset_real(tmp_path):
    relatorio = executar("todos", pasta_saida=tmp_path)
    assert not relatorio["violacoes"], "\n".join(relatorio["violacoes"])
