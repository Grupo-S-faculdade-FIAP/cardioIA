"""Saída esperada do extrator nos 10 relatos (SDD Fase 2, R1, R4, R5)."""

import json
from pathlib import Path

import pytest

from analisador_clinico import analisar_relato
from extrator_sintomas import extrair_atributos, extrair_conceitos

ESPERADO = {
    chave: valor
    for chave, valor in json.loads(
        (Path(__file__).parent / "golden" / "relatos_esperados.json").read_text(encoding="utf-8")
    ).items()
    if not chave.startswith("_")
}


# Pendências conhecidas (SDD §7) viram xfail estrito: quando corrigidas, o teste exige remover a pendência.
CASOS_CONDICAO = [
    pytest.param(r, marks=pytest.mark.xfail(reason=ESPERADO[r]["pendencia"])) if "pendencia" in ESPERADO[r] else r
    for r in sorted(ESPERADO)
]


def test_dez_relatos(relatos):
    assert sorted(relatos) == sorted(ESPERADO)


@pytest.mark.parametrize("relato_id", sorted(ESPERADO))
def test_conceitos_obrigatorios(relato_id, relatos, base):
    encontrados = {c["conceito_id"] for c in extrair_conceitos(relatos[relato_id], base["expressoes"])}
    faltando = set(ESPERADO[relato_id]["conceitos"]) - encontrados
    assert not faltando, f"{relato_id}: conceitos não detectados {sorted(faltando)}"


@pytest.mark.parametrize("relato_id", sorted(ESPERADO))
def test_atributos_obrigatorios(relato_id, relatos, base):
    encontrados = {a["atributo_id"] for a in extrair_atributos(relatos[relato_id], base["atributos"])}
    faltando = set(ESPERADO[relato_id]["atributos"]) - encontrados
    assert not faltando, f"{relato_id}: atributos não detectados {sorted(faltando)}"


@pytest.mark.parametrize("relato_id", CASOS_CONDICAO)
def test_condicao_principal_unica_e_correta(relato_id, relatos, base):
    analise = analisar_relato(relatos[relato_id], base)
    sugestao = analise["sugestao"]
    assert len(sugestao["empatadas"]) == 1, f"{relato_id}: empate entre {sugestao['empatadas']}"
    assert sugestao["condicao"] == ESPERADO[relato_id]["condicao_principal"]

    if "segunda_hipotese" in ESPERADO[relato_id]:
        assert analise["condicoes"][1]["condicao"] == ESPERADO[relato_id]["segunda_hipotese"]


@pytest.mark.parametrize("relato_id", sorted(ESPERADO))
def test_relatos_nao_tem_sintoma_negado(relato_id, relatos, base):
    """Nenhum dos 10 relatos nega sintoma; negação indevida apagaria evidência."""
    assert analisar_relato(relatos[relato_id], base)["conceitos_negados"] == []
