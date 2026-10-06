"""Testes de comportamento do extrator (SDD Fase 2, R6 e §6)."""

import pytest

from extrator_sintomas import extrair_conceitos


def _conceitos(texto, base):
    return {c["conceito_id"] for c in extrair_conceitos(texto, base["expressoes"])}


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


@pytest.mark.xfail(reason="negação não implementada — SDD §7 / R6")
@pytest.mark.parametrize("frase,conceito_negado", [
    ("Não sinto dor no peito nem falta de ar.", "S013"),
    ("Não tenho falta de ar.", "S001"),
    ("Sem inchaço nas pernas.", "S021"),
])
def test_sintoma_negado_nao_e_extraido(frase, conceito_negado, base):
    assert conceito_negado not in _conceitos(frase, base)
