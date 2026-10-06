"""Relaciona os conceitos extraídos às associações da base de conhecimento."""

from extrator_sintomas import extrair_atributos, extrair_conceitos

# Peso de cada evidência conforme o tipo de relação registrado na base
# (SDD Fase 2, §3.2). Sintomas típicos e manifestações principais pesam mais
# que sintomas associados ou compartilhados — assim a dispneia, presente em
# quase todas as condições, não decide sozinha a sugestão.
PESOS_RELACAO = {
    "manifestação principal": 3,
    "sintoma típico": 2,
    "manifestação contextual": 2,
    "sintoma menos típico": 1,
    "sintoma associado": 1,
    "manifestação compartilhada": 1,
}

# Cada atributo de contexto relevante encontrado (esforço, irradiação...) soma 1.
PESO_ATRIBUTO = 1


def criar_indice_conceitos(conceitos):
    """Permite localizar rapidamente o nome de um conceito pelo seu ID."""
    return {item["conceito_id"]: item for item in conceitos}


def analisar_associacoes(conceitos_encontrados, atributos_encontrados, associacoes):
    """
    Reúne as associações possíveis para os conceitos detectados.

    O programa NÃO confirma diagnósticos. Ele recupera associações registradas
    na knowledge_base e mostra quais atributos relevantes também apareceram.
    Conceitos e atributos negados pelo paciente são ignorados.
    """
    ids_conceitos = {
        item["conceito_id"] for item in conceitos_encontrados if not item.get("negado")
    }
    ids_atributos = {
        item["atributo_id"] for item in atributos_encontrados if not item.get("negado")
    }

    resultados = []

    for associacao in associacoes:
        if associacao["conceito_id"] not in ids_conceitos:
            continue

        atributos_esperados = {
            item for item in associacao["atributos_relevantes"].split("|")
            if item
        }

        atributos_presentes = sorted(atributos_esperados & ids_atributos)

        resultados.append({
            "associacao_id": associacao["associacao_id"],
            "conceito_id": associacao["conceito_id"],
            "condicao": associacao["condicao_associada"],
            "tipo_relacao": associacao["tipo_relacao"],
            "peso": PESOS_RELACAO[associacao["tipo_relacao"]],
            "fontes": associacao["fonte_id"].split("|"),
            "atributos_presentes": atributos_presentes,
            "observacao": associacao["observacao"],
        })

    return resultados


def agrupar_por_condicao(associacoes_encontradas):
    """
    Agrupa evidências que apontam para a mesma condição.

    A pontuação é apenas uma forma transparente de ordenar resultados:
    soma do peso de cada evidência (PESOS_RELACAO)
    + PESO_ATRIBUTO por atributo contextual relevante encontrado.

    Ela NÃO representa probabilidade médica.
    """
    grupos = {}

    for item in associacoes_encontradas:
        condicao = item["condicao"]

        if condicao not in grupos:
            grupos[condicao] = {
                "condicao": condicao,
                "evidencias": [],
                "atributos": set(),
                "fontes": set(),
            }

        grupos[condicao]["evidencias"].append({
            "conceito_id": item["conceito_id"],
            "tipo_relacao": item["tipo_relacao"],
            "peso": item["peso"],
        })
        grupos[condicao]["atributos"].update(item["atributos_presentes"])
        grupos[condicao]["fontes"].update(item["fontes"])

    resultado = []

    for grupo in grupos.values():
        grupo["atributos"] = sorted(grupo["atributos"])
        grupo["fontes"] = sorted(grupo["fontes"])
        grupo["pontuacao_explicativa"] = (
            sum(evidencia["peso"] for evidencia in grupo["evidencias"])
            + PESO_ATRIBUTO * len(grupo["atributos"])
        )
        resultado.append(grupo)

    # Desempate pelo nome só para a ordem ser sempre a mesma; a sugestão
    # principal não usa esse critério (ver sugerir_condicao_principal).
    return sorted(
        resultado,
        key=lambda item: (-item["pontuacao_explicativa"], item["condicao"]),
    )


def sugerir_condicao_principal(condicoes):
    """
    Escolhe a condição de maior pontuação.

    Empate no topo não é desfeito às cegas: a sugestão fica vazia
    (resultado inconclusivo) e as condições empatadas são devolvidas.
    """
    if not condicoes:
        return {"condicao": None, "empatadas": [], "pontuacao": 0}

    maior = condicoes[0]["pontuacao_explicativa"]
    empatadas = [
        item["condicao"] for item in condicoes
        if item["pontuacao_explicativa"] == maior
    ]

    return {
        "condicao": empatadas[0] if len(empatadas) == 1 else None,
        "empatadas": empatadas,
        "pontuacao": maior,
    }


def analisar_relato(texto, base):
    """Pipeline completo da Parte 1: extração → associações → sugestão."""
    conceitos = extrair_conceitos(texto, base["expressoes"], incluir_negados=True)
    atributos = extrair_atributos(texto, base["atributos"], incluir_negados=True)
    condicoes = agrupar_por_condicao(
        analisar_associacoes(conceitos, atributos, base["associacoes"])
    )

    return {
        "conceitos": [item for item in conceitos if not item["negado"]],
        "conceitos_negados": [item for item in conceitos if item["negado"]],
        "atributos": [item for item in atributos if not item["negado"]],
        "condicoes": condicoes,
        "sugestao": sugerir_condicao_principal(condicoes),
    }
