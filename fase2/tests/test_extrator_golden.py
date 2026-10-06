"""Saída esperada do extrator nos 10 relatos (SDD Fase 2, R1, R4, R5)."""

import json
from pathlib import Path

import pytest

from analisador_clinico import agrupar_por_condicao, analisar_associacoes
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
    texto = relatos[relato_id]
    condicoes = agrupar_por_condicao(analisar_associacoes(
        extrair_conceitos(texto, base["expressoes"]),
        extrair_atributos(texto, base["atributos"]),
        base["associacoes"],
    ))
    assert condicoes, f"{relato_id}: nenhuma condição sugerida"
    primeira = condicoes[0]
    empatadas = [c["condicao"] for c in condicoes if c["pontuacao_explicativa"] == primeira["pontuacao_explicativa"]]
    assert len(empatadas) == 1, f"{relato_id}: empate entre {empatadas}"
    assert primeira["condicao"] == ESPERADO[relato_id]["condicao_principal"]
