"""Testes de comportamento do extrator (SDD Fase 2, R6, §3.1 e §6)."""

import pytest

from analisador_clinico import analisar_relato
from extrator_sintomas import extrair_atributos, extrair_conceitos, normalizar_texto, tokenizar
from vieses import trocar_genero

RELATOS = [f"RELATO {numero:02d}" for numero in range(1, 11)]


def _conceitos(texto, base):
    return {c["conceito_id"] for c in extrair_conceitos(texto, base["expressoes"])}


def _negados(texto, base):
    return {
        c["conceito_id"]
        for c in extrair_conceitos(texto, base["expressoes"], incluir_negados=True)
        if c["negado"]
    }


def _atributos(texto, base):
    return {a["atributo_id"] for a in extrair_atributos(texto, base["atributos"])}


# --- Invariâncias -------------------------------------------------------------

@pytest.mark.parametrize("com_acento,sem_acento", [
    ("Estou com pressão no peito.", "Estou com pressao no peito."),
    ("Fiquei tonta e muito pálida.", "Fiquei tonta e muito palida."),
    ("Sinto náusea e tontura.", "Sinto nausea e tontura."),
])
def test_invariante_a_acento(com_acento, sem_acento, base):
    assert _conceitos(com_acento, base) == _conceitos(sem_acento, base)


@pytest.mark.parametrize("masculino,feminino", [
    ("Estou muito cansado e fiquei tonto.", "Estou muito cansada e fiquei tonta."),
    ("Fiquei pálido e quase desmaiei.", "Fiquei pálida e quase desmaiei."),
])
def test_invariante_a_genero(masculino, feminino, base):
    assert _conceitos(masculino, base) == _conceitos(feminino, base)


def test_invariante_a_maiusculas(base):
    assert _conceitos("DOR NO PEITO E FALTA DE AR", base) == _conceitos("dor no peito e falta de ar", base)


@pytest.mark.parametrize("relato_id", RELATOS)
def test_relato_escrito_por_mulher_tem_a_mesma_analise(relato_id, relatos, base):
    """Contrafactual de gênero nos 10 relatos (SDD §3, regra 10)."""
    original = analisar_relato(relatos[relato_id], base)
    trocado = analisar_relato(trocar_genero(relatos[relato_id]), base)

    assert {c["conceito_id"] for c in trocado["conceitos"]} == {c["conceito_id"] for c in original["conceitos"]}
    assert {a["atributo_id"] for a in trocado["atributos"]} == {a["atributo_id"] for a in original["atributos"]}
    assert trocado["sugestao"] == original["sugestao"]


# --- Negação (§3.1) -----------------------------------------------------------

@pytest.mark.parametrize("frase,negados", [
    ("Não sinto dor no peito nem falta de ar.", {"S013", "S001"}),
    ("Não tenho falta de ar.", {"S001"}),
    ("Sem inchaço nas pernas.", {"S021"}),
    ("Nunca desmaiei na vida.", {"S018"}),
    ("Não sinto mais aquela dor no peito.", {"S013"}),
    ("Estou sem nenhuma dor no peito hoje.", {"S013"}),
    ("Não acordo de madrugada com falta de ar.", {"S003", "S001"}),
])
def test_sintoma_negado_nao_e_extraido(frase, negados, base):
    assert not negados & _conceitos(frase, base)
    assert negados <= _negados(frase, base), "negado deve continuar disponível para exibição"


@pytest.mark.parametrize("frase,afirmado", [
    ("Não sinto dor no peito, só um cansaço leve.", "S004"),
    ("Não tenho dor no peito, mas tenho falta de ar.", "S001"),
    ("Não tenho dor no peito mas fico sem ar.", "S001"),
    ("Não tenho febre e estou com falta de ar há dias.", "S001"),
    ("Não aguento mais esse cansaço.", "S004"),
    ("Não consigo dormir de tanta falta de ar.", "S001"),
    ("A dor não melhorou e estou suando muito.", "S014"),
    ("Não tenho dor no peito em repouso, mas sinto dor no peito quando subo escadas.", "S013"),
])
def test_sintoma_fora_do_alcance_da_negacao_e_extraido(frase, afirmado, base):
    assert afirmado in _conceitos(frase, base)


def test_quase_desmaiar_e_pre_sincope_e_nao_sincope(base):
    encontrados = _conceitos("Fiquei pálida e quase desmaiei.", base)
    assert "S017" in encontrados
    assert "S018" not in encontrados


def test_sem_de_expressao_nao_nega_o_contexto_seguinte(base):
    # O "sem" de "fico sem ar" não pode negar "quando caminho" (RELATO 01 e 08).
    assert "A003" in _atributos("Fico sem ar quando caminho até a padaria.", base)


def test_negacao_do_alivio_com_repouso(base):
    atributos = _atributos("A dor no peito não melhora quando descanso.", base)
    assert "A007" in atributos
    assert "A006" not in atributos


@pytest.mark.xfail(reason="dupla negação não tratada — SDD §7")
def test_dupla_negacao(base):
    assert "S001" in _conceitos("Não consigo fazer nada sem falta de ar.", base)


def test_tokenizar_preserva_as_palavras_de_normalizar_texto(relatos):
    for texto in relatos.values():
        assert tokenizar(texto)[0] == normalizar_texto(texto).split()
