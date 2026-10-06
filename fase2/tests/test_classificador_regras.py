"""Linha de base por regras (SDD Fase 2, §4.1)."""

import pytest

from classificador_regras import ALTO, BAIXO, classificar_por_regras


@pytest.mark.parametrize("frase,motivo", [
    ("Estou com dor no peito que vai para o braço.", "A1"),
    ("Sinto aperto no peito há mais de vinte minutos.", "A1"),
    ("Tenho dor no peito com falta de ar.", "A1"),
    ("Desmaiei no trabalho.", "A2"),
    ("Acordo de madrugada com falta de ar.", "A3"),
    ("Fiquei com falta de ar de repente.", "A3"),
    ("Comecei a suar frio e sentir enjoo.", "A4"),
    ("De repente fiquei muito cansada e com mal-estar.", "A4"),
])
def test_cada_criterio_de_alarme(frase, motivo, base):
    situacao, motivos = classificar_por_regras(frase, base)
    assert situacao == ALTO
    assert any(m.startswith(motivo) for m in motivos)


@pytest.mark.parametrize("frase", [
    "Sinto pressão no peito quando subo escadas e melhora quando descanso, há meses.",  # angina estável
    "Tenho uma falta de ar leve quando subo escadas há anos.",
    "Fiquei pálida e quase desmaiei.",                     # pré-síncope isolada não é A2
    "Não sinto dor no peito nem falta de ar, só cansaço.",  # negação
    "Estou com dor de cabeça leve desde ontem.",
])
def test_sem_sinal_de_alarme_e_baixo_risco(frase, base):
    assert classificar_por_regras(frase, base) == (BAIXO, [])


def test_vocabulario_fora_da_base_nao_e_reconhecido(base):
    """Limitação conhecida (SDD §7): coloquialismo some para as regras."""
    assert classificar_por_regras("Apaguei por uns segundos no ônibus.", base)[0] == BAIXO
