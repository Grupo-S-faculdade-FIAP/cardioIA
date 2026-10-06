"""Contrato do dataset de risco (SDD Fase 2, §4 / R7)."""

import pytest

from contrato_dataset import ARQUIVO_DATASET, carregar_dataset_risco, validar_dataset_risco


def test_dataset_valido_nao_tem_erros(dataset_sintetico):
    assert validar_dataset_risco(dataset_sintetico) == []


def test_coluna_ausente(dataset_sintetico):
    erros = validar_dataset_risco(dataset_sintetico.drop(columns="particao"))
    assert erros == ["colunas ausentes: ['particao']"]


@pytest.mark.parametrize("coluna,valor", [
    ("situacao", "risco medio"),
    ("origem", "chatgpt"),
    ("particao", "validacao"),
])
def test_valor_fora_do_contrato(dataset_sintetico, coluna, valor):
    dataset_sintetico.loc[0, coluna] = valor
    assert any(f"'{coluna}'" in e for e in validar_dataset_risco(dataset_sintetico))


def test_template_no_teste_e_proibido(dataset_sintetico):
    linha = dataset_sintetico.index[dataset_sintetico["particao"] == "teste"][0]
    dataset_sintetico.loc[linha, "origem"] = "template"
    assert any("só frases manuais" in e for e in validar_dataset_risco(dataset_sintetico))


def test_duplicata_normalizada_entre_treino_e_teste(dataset_sintetico):
    teste = dataset_sintetico.index[dataset_sintetico["particao"] == "teste"][0]
    treino = dataset_sintetico.index[dataset_sintetico["particao"] == "treino"][0]
    dataset_sintetico.loc[treino, "frase"] = dataset_sintetico.loc[teste, "frase"].upper() + "!"
    assert any("duplicadas" in e for e in validar_dataset_risco(dataset_sintetico))


def test_frase_vazia(dataset_sintetico):
    dataset_sintetico.loc[0, "frase"] = "   "
    assert any("vazias" in e for e in validar_dataset_risco(dataset_sintetico))


def test_tamanho_minimo(dataset_sintetico):
    erros = validar_dataset_risco(dataset_sintetico.head(100))
    assert any("mínimo 200" in e for e in erros)


def test_desbalanceamento(dataset_sintetico):
    alto = dataset_sintetico[dataset_sintetico["situacao"] == "alto risco"]
    erros = validar_dataset_risco(dataset_sintetico.drop(alto.index[30:]), tamanho_minimo=0)
    assert any("classe 'alto risco'" in e for e in erros)


@pytest.mark.skipif(not ARQUIVO_DATASET.exists(), reason="frases_risco.csv ainda não criado")
def test_dataset_real_cumpre_contrato():
    erros = validar_dataset_risco(carregar_dataset_risco())
    assert not erros, "\n".join(erros)
