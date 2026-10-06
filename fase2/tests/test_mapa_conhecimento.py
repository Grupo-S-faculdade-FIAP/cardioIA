"""Mapa achatado no formato do enunciado (SDD Fase 2, §3 regra 12 / R3)."""

import csv

from gerar_mapa_conhecimento import ARQUIVO_MAPA, COLUNAS_MAPA, gerar_linhas_mapa


def _ler_mapa():
    with ARQUIVO_MAPA.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def test_colunas_no_formato_do_enunciado():
    with ARQUIVO_MAPA.open(encoding="utf-8-sig", newline="") as arquivo:
        cabecalho = next(csv.reader(arquivo))
    assert cabecalho[:3] == ["sintoma_1", "sintoma_2", "doenca_associada"]
    assert cabecalho == COLUNAS_MAPA


def test_mapa_sincronizado_com_a_base(base):
    assert _ler_mapa() == gerar_linhas_mapa(base), (
        "mapa_conhecimento.csv desatualizado: rode python fase2/src/gerar_mapa_conhecimento.py"
    )


def test_mapa_cobre_todas_as_expressoes_e_associacoes(base):
    linhas = _ler_mapa()
    no_mapa = {linha["sintoma_1"] for linha in linhas} | {linha["sintoma_2"] for linha in linhas}
    assert {e["expressao"] for e in base["expressoes"]} <= no_mapa
    assert {linha["associacao_id"] for linha in linhas} == {a["associacao_id"] for a in base["associacoes"]}
