"""Contrato do dataset de risco (SDD Fase 2, §4 / R7)."""

import json

import pytest

from classificador_regras import classificar_por_regras
from contrato_dataset import (
    ARQUIVO_DATASET,
    ARQUIVO_TESTE_CONGELADO,
    carregar_dataset_risco,
    hash_conjunto_teste,
    validar_dataset_risco,
)
from gerar_frases_risco import gerar_dataset

dataset_real = pytest.mark.skipif(not ARQUIVO_DATASET.exists(), reason="frases_risco.csv ainda não criado")


def test_dataset_valido_nao_tem_erros(dataset_sintetico):
    assert validar_dataset_risco(dataset_sintetico) == []


def test_coluna_ausente(dataset_sintetico):
    erros = validar_dataset_risco(dataset_sintetico.drop(columns="particao"))
    assert erros == ["colunas ausentes: ['particao']"]


@pytest.mark.parametrize("coluna,valor", [
    ("situacao", "risco medio"),
    ("origem", "chatgpt"),
    ("particao", "validacao"),
    ("criterio", "Z9"),
])
def test_valor_fora_do_contrato(dataset_sintetico, coluna, valor):
    dataset_sintetico.loc[0, coluna] = valor
    assert any(f"'{coluna}'" in e for e in validar_dataset_risco(dataset_sintetico))


def test_criterio_incoerente_com_a_situacao(dataset_sintetico):
    linha = dataset_sintetico.index[dataset_sintetico["situacao"] == "alto risco"][0]
    dataset_sintetico.loc[linha, "criterio"] = "B1"
    assert any("incoerente" in e for e in validar_dataset_risco(dataset_sintetico))


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


def test_hash_do_teste_muda_com_qualquer_edicao(dataset_sintetico):
    original = hash_conjunto_teste(dataset_sintetico)
    linha = dataset_sintetico.index[dataset_sintetico["particao"] == "teste"][0]
    dataset_sintetico.loc[linha, "frase"] += " "
    assert hash_conjunto_teste(dataset_sintetico) != original


# --- Dataset real -------------------------------------------------------------

@dataset_real
def test_dataset_real_cumpre_contrato():
    erros = validar_dataset_risco(carregar_dataset_risco())
    assert not erros, "\n".join(erros)


@dataset_real
def test_dataset_sincronizado_com_as_fontes(base):
    assert carregar_dataset_risco().to_dict("records") == gerar_dataset(base), (
        "frases_risco.csv desatualizado: rode python fase2/src/gerar_frases_risco.py"
    )


@dataset_real
def test_conjunto_de_teste_congelado():
    congelado = json.loads(ARQUIVO_TESTE_CONGELADO.read_text(encoding="utf-8"))
    df = carregar_dataset_risco()
    assert (df["particao"] == "teste").sum() == congelado["linhas_de_teste"]
    assert hash_conjunto_teste(df) == congelado["sha256"], (
        "o conjunto de teste mudou: exige aprovação da equipe, revisão clínica e novo hash (CLAUDE.md §2)"
    )


@dataset_real
def test_templates_seguem_o_criterio_de_rotulo(base):
    templates = carregar_dataset_risco().query("origem == 'template'")
    divergentes = [
        (frase, situacao)
        for frase, situacao in zip(templates["frase"], templates["situacao"])
        if classificar_por_regras(frase, base)[0] != situacao
    ]
    assert not divergentes, divergentes
