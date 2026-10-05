"""Relaciona os conceitos extraídos às associações da base de conhecimento."""


def criar_indice_conceitos(conceitos):
    """Permite localizar rapidamente o nome de um conceito pelo seu ID."""
    return {item["conceito_id"]: item for item in conceitos}


def analisar_associacoes(conceitos_encontrados, atributos_encontrados, associacoes):
    """
    Reúne as associações possíveis para os conceitos detectados.

    O programa NÃO confirma diagnósticos. Ele recupera associações registradas
    na knowledge_base e mostra quais atributos relevantes também apareceram.
    """
    ids_conceitos = {item["conceito_id"] for item in conceitos_encontrados}
    ids_atributos = {item["atributo_id"] for item in atributos_encontrados}

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
            "fontes": associacao["fonte_id"].split("|"),
            "atributos_presentes": atributos_presentes,
            "observacao": associacao["observacao"],
        })

    return resultados


def agrupar_por_condicao(associacoes_encontradas):
    """
    Agrupa evidências que apontam para a mesma condição.

    A pontuação é apenas uma forma transparente de ordenar resultados:
    +1 por conceito associado encontrado
    +1 por atributo contextual relevante encontrado

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
        })
        grupos[condicao]["atributos"].update(item["atributos_presentes"])
        grupos[condicao]["fontes"].update(item["fontes"])

    resultado = []

    for grupo in grupos.values():
        grupo["atributos"] = sorted(grupo["atributos"])
        grupo["fontes"] = sorted(grupo["fontes"])
        grupo["pontuacao_explicativa"] = (
            len(grupo["evidencias"]) + len(grupo["atributos"])
        )
        resultado.append(grupo)

    return sorted(
        resultado,
        key=lambda item: item["pontuacao_explicativa"],
        reverse=True,
    )
