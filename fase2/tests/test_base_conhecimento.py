"""Contrato da base de conhecimento (SDD Fase 2, §3)."""

import csv
import re

import pytest

from analisador_clinico import PESOS_RELACAO
from carregador_base import PASTA_BASE
from extrator_sintomas import GATILHOS_NEGACAO, PSEUDO_NEGACOES, normalizar_texto
from vieses import tem_marca_de_genero, trocar_genero

PADROES_ID = {
    "conceitos.csv": ("conceito_id", r"S\d{3}"),
    "expressoes.csv": ("expressao_id", r"E\d{3}"),
    "atributos.csv": ("atributo_id", r"A\d{3}"),
    "associacoes.csv": ("associacao_id", r"AS\d{3}"),
    "fontes.csv": ("fonte_id", r"F\d{3}"),
}


def _ids(linhas, coluna):
    return {linha[coluna] for linha in linhas}


def _lista(valor):
    return [item for item in valor.split("|") if item]


@pytest.fixture(scope="module")
def fontes():
    with (PASTA_BASE / "fontes.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


@pytest.mark.parametrize("arquivo", sorted(PADROES_ID))
def test_numero_de_colunas_consistente(arquivo):
    with (PASTA_BASE / arquivo).open(encoding="utf-8-sig", newline="") as f:
        cabecalho, *linhas = list(csv.reader(f))
    erradas = [linha[0] for linha in linhas if len(linha) != len(cabecalho)]
    assert not erradas, f"{arquivo}: linhas com nº de colunas diferente do cabeçalho: {erradas}"


@pytest.mark.parametrize("arquivo", sorted(PADROES_ID))
def test_ids_unicos_e_no_padrao(arquivo):
    coluna, padrao = PADROES_ID[arquivo]
    with (PASTA_BASE / arquivo).open(encoding="utf-8-sig", newline="") as f:
        ids = [linha[coluna] for linha in csv.DictReader(f)]
    fora_do_padrao = [i for i in ids if not re.fullmatch(padrao, i)]
    duplicados = sorted({i for i in ids if ids.count(i) > 1})
    assert not fora_do_padrao, f"{arquivo}: IDs fora do padrão {padrao}: {fora_do_padrao}"
    assert not duplicados, f"{arquivo}: IDs duplicados: {duplicados}"


def test_expressoes_apontam_para_conceitos_existentes(base):
    conceitos = _ids(base["conceitos"], "conceito_id")
    orfas = [e["expressao_id"] for e in base["expressoes"] if e["conceito_id"] not in conceitos]
    assert not orfas


def test_associacoes_apontam_para_conceitos_fontes_e_atributos(base, fontes):
    conceitos = _ids(base["conceitos"], "conceito_id")
    atributos = _ids(base["atributos"], "atributo_id")
    ids_fontes = _ids(fontes, "fonte_id")
    erros = []
    for a in base["associacoes"]:
        if a["conceito_id"] not in conceitos:
            erros.append(f"{a['associacao_id']}: conceito {a['conceito_id']} inexistente")
        if not _lista(a["fonte_id"]):
            erros.append(f"{a['associacao_id']}: sem fonte")
        erros += [f"{a['associacao_id']}: fonte {f} inexistente" for f in _lista(a["fonte_id"]) if f not in ids_fontes]
        erros += [
            f"{a['associacao_id']}: atributo {x} inexistente"
            for x in _lista(a["atributos_relevantes"])
            if x not in atributos
        ]
    assert not erros, "\n".join(erros)


def test_todo_conceito_tem_expressao_e_associacao(base):
    com_expressao = _ids(base["expressoes"], "conceito_id")
    com_associacao = _ids(base["associacoes"], "conceito_id")
    conceitos = _ids(base["conceitos"], "conceito_id")
    assert not conceitos - com_expressao, "conceitos sem expressão"
    assert not conceitos - com_associacao, "conceitos sem associação"


def test_toda_fonte_e_usada(base, fontes):
    usadas = {f for a in base["associacoes"] for f in _lista(a["fonte_id"])}
    assert not _ids(fontes, "fonte_id") - usadas, "fontes cadastradas e não usadas"


def test_expressao_nao_pertence_a_dois_conceitos(base):
    conceito_por_expressao = {}
    conflitos = []
    for e in base["expressoes"]:
        chave = normalizar_texto(e["expressao"])
        anterior = conceito_por_expressao.setdefault(chave, e["conceito_id"])
        if anterior != e["conceito_id"]:
            conflitos.append(f"'{e['expressao']}': {anterior} e {e['conceito_id']}")
    assert not conflitos, "\n".join(conflitos)


@pytest.mark.parametrize("tabela,colunas", [
    ("conceitos", ["conceito_id", "conceito_clinico", "categoria"]),
    ("expressoes", ["expressao_id", "conceito_id", "expressao", "origem_expressao"]),
    ("atributos", ["atributo_id", "tipo", "valor_normalizado", "expressoes_gatilho"]),
    ("associacoes", ["associacao_id", "conceito_id", "condicao_associada", "tipo_relacao", "fonte_id"]),
])
def test_campos_obrigatorios_preenchidos(base, tabela, colunas):
    vazios = [
        f"{linha[colunas[0]]}.{coluna}"
        for linha in base[tabela]
        for coluna in colunas
        if not (linha.get(coluna) or "").strip()
    ]
    assert not vazios, f"{tabela}: campos vazios {vazios}"


def test_todo_atributo_tem_gatilho(base):
    sem_gatilho = [a["atributo_id"] for a in base["atributos"] if not _lista(a["expressoes_gatilho"])]
    assert not sem_gatilho


def test_tipo_relacao_tem_peso_definido(base):
    sem_peso = sorted({a["tipo_relacao"] for a in base["associacoes"]} - set(PESOS_RELACAO))
    assert not sem_peso, f"tipo_relacao sem peso em PESOS_RELACAO (SDD §3.2): {sem_peso}"


def test_par_conceito_condicao_unico(base):
    pares = [(a["conceito_id"], a["condicao_associada"]) for a in base["associacoes"]]
    repetidos = sorted({par for par in pares if pares.count(par) > 1})
    assert not repetidos, f"pares (conceito, condição) repetidos: {repetidos}"


def _frases_da_base(base):
    """Pares (dono, frase): expressões pertencem a um conceito; gatilhos, a um atributo."""
    frases = [(e["conceito_id"], e["expressao"]) for e in base["expressoes"]]
    frases += [(a["atributo_id"], g) for a in base["atributos"] for g in _lista(a["expressoes_gatilho"])]
    return frases


def test_paridade_de_genero(base):
    frases_do_dono = {}
    for dono, frase in _frases_da_base(base):
        frases_do_dono.setdefault(dono, set()).add(normalizar_texto(frase))

    faltando = [
        f"{dono}: tem '{frase}' mas não '{trocar_genero(frase)}'"
        for dono, frase in _frases_da_base(base)
        if tem_marca_de_genero(frase) and normalizar_texto(trocar_genero(frase)) not in frases_do_dono[dono]
    ]
    assert not faltando, "SDD §3, regra 10:\n" + "\n".join(faltando)


def test_gatilho_de_negacao_dentro_de_expressao_e_pseudo_negacao(base):
    locucoes = [tuple(p.split()) for p in PSEUDO_NEGACOES]
    erros = []
    for dono, frase in _frases_da_base(base):
        tokens = normalizar_texto(frase).split()
        for posicao, token in enumerate(tokens):
            if token in GATILHOS_NEGACAO and not any(
                tuple(tokens[posicao:posicao + len(locucao)]) == locucao for locucao in locucoes
            ):
                erros.append(f"{dono}: '{frase}' — '{token}' negaria o sintoma seguinte")
    assert not erros, "SDD §3, regra 11 (cadastre a locução em PSEUDO_NEGACOES):\n" + "\n".join(erros)
