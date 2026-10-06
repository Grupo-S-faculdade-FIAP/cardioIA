"""Pontuação e sugestão de condição (SDD Fase 2, §3.2 / R5)."""

from analisador_clinico import (
    PESO_ATRIBUTO,
    PESOS_RELACAO,
    agrupar_por_condicao,
    analisar_associacoes,
    analisar_relato,
    sugerir_condicao_principal,
)


def _associacao(associacao_id, conceito_id, condicao, tipo, atributos=""):
    return {
        "associacao_id": associacao_id,
        "conceito_id": conceito_id,
        "condicao_associada": condicao,
        "tipo_relacao": tipo,
        "fonte_id": "F001",
        "atributos_relevantes": atributos,
        "observacao": "",
    }


ASSOCIACOES = [
    _associacao("AS1", "S1", "Doença A", "manifestação principal", "A1|A2"),
    _associacao("AS2", "S2", "Doença A", "sintoma associado"),
    _associacao("AS3", "S2", "Doença B", "sintoma típico", "A2"),
    _associacao("AS4", "S3", "Doença B", "sintoma típico"),
    _associacao("AS5", "S3", "Doença C", "sintoma típico"),
]


def _condicoes(conceitos, atributos=()):
    return agrupar_por_condicao(analisar_associacoes(
        [{"conceito_id": c} for c in conceitos],
        [{"atributo_id": a} for a in atributos],
        ASSOCIACOES,
    ))


def test_pontuacao_soma_peso_das_evidencias_e_atributos():
    pontuacoes = {
        c["condicao"]: c["pontuacao_explicativa"]
        for c in _condicoes(["S1", "S2"], ["A1", "A2", "A9"])
    }
    assert pontuacoes == {
        "Doença A": PESOS_RELACAO["manifestação principal"] + PESOS_RELACAO["sintoma associado"] + 2 * PESO_ATRIBUTO,
        "Doença B": PESOS_RELACAO["sintoma típico"] + PESO_ATRIBUTO,
    }


def test_evidencia_registra_o_peso_usado():
    evidencias = _condicoes(["S1"])[0]["evidencias"]
    assert evidencias == [{"conceito_id": "S1", "tipo_relacao": "manifestação principal", "peso": 3}]


def test_conceito_e_atributo_negados_nao_pontuam():
    condicoes = agrupar_por_condicao(analisar_associacoes(
        [{"conceito_id": "S1", "negado": True}, {"conceito_id": "S2"}],
        [{"atributo_id": "A2", "negado": True}],
        ASSOCIACOES,
    ))
    assert {e["conceito_id"] for c in condicoes for e in c["evidencias"]} == {"S2"}
    assert all(not c["atributos"] for c in condicoes)


def test_sugestao_unica():
    sugestao = sugerir_condicao_principal(_condicoes(["S1", "S2"]))
    assert sugestao == {"condicao": "Doença A", "empatadas": ["Doença A"], "pontuacao": 4}


def test_empate_no_topo_deixa_a_sugestao_inconclusiva():
    condicoes = _condicoes(["S3"])
    assert [c["condicao"] for c in condicoes] == ["Doença B", "Doença C"]  # ordem determinística
    assert sugerir_condicao_principal(condicoes) == {
        "condicao": None,
        "empatadas": ["Doença B", "Doença C"],
        "pontuacao": 2,
    }


def test_sem_evidencia_nao_ha_sugestao():
    assert sugerir_condicao_principal([]) == {"condicao": None, "empatadas": [], "pontuacao": 0}


def test_analisar_relato_separa_sintomas_negados(base):
    analise = analisar_relato("Não sinto dor no peito, mas estou com falta de ar quando me deito.", base)
    assert {c["conceito_id"] for c in analise["conceitos_negados"]} == {"S013"}
    assert {"S001", "S002"} <= {c["conceito_id"] for c in analise["conceitos"]}
    assert analise["sugestao"]["condicao"] == "Insuficiência Cardíaca"
