"""Ponto de entrada da Parte 1 do CardioIA."""

from carregador_base import carregar_base_conhecimento, carregar_relatos
from extrator_sintomas import extrair_conceitos, extrair_atributos
from analisador_clinico import (
    analisar_associacoes,
    agrupar_por_condicao,
    criar_indice_conceitos,
)


def exibir_resultado(relato, conceitos, atributos, condicoes, indice_conceitos):
    """Mostra a análise em formato legível e explicável."""
    print("\n" + "=" * 80)
    print(relato["id"])
    print("=" * 80)
    print(relato["texto"])

    print("\nCONCEITOS ENCONTRADOS:")
    if not conceitos:
        print("- Nenhum conceito cadastrado foi identificado.")
    else:
        for item in conceitos:
            nome = indice_conceitos[item["conceito_id"]]["conceito_clinico"]
            expressoes = ", ".join(item["expressoes_encontradas"])
            print(f"- {item['conceito_id']} | {nome}")
            print(f"  Expressão detectada: {expressoes}")

    print("\nATRIBUTOS/CONTEXTO:")
    if not atributos:
        print("- Nenhum atributo cadastrado foi identificado.")
    else:
        for item in atributos:
            print(
                f"- {item['atributo_id']} | "
                f"{item['tipo']}: {item['valor']}"
            )

    print("\nPOSSÍVEIS ASSOCIAÇÕES DA BASE:")
    if not condicoes:
        print("- Nenhuma associação disponível para os conceitos detectados.")
    else:
        for item in condicoes:
            print(
                f"- {item['condicao']} "
                f"(pontuação explicativa: {item['pontuacao_explicativa']})"
            )

            evidencias = []
            for evidencia in item["evidencias"]:
                nome = indice_conceitos[evidencia["conceito_id"]]["conceito_clinico"]
                evidencias.append(
                    f"{nome} [{evidencia['tipo_relacao']}]"
                )

            print("  Evidências: " + "; ".join(evidencias))

            if item["atributos"]:
                print("  Contextos: " + ", ".join(item["atributos"]))

            print("  Fontes cadastradas: " + ", ".join(item["fontes"]))

    print(
        "\nAVISO: resultado educacional baseado em associações da knowledge_base; "
        "não representa diagnóstico médico."
    )


def main():
    """Executa o pipeline completo para todos os relatos."""
    base = carregar_base_conhecimento()
    relatos = carregar_relatos()
    indice_conceitos = criar_indice_conceitos(base["conceitos"])

    print(f"CardioIA: {len(relatos)} relatos carregados.")

    for relato in relatos:
        conceitos = extrair_conceitos(
            relato["texto"],
            base["expressoes"],
        )

        atributos = extrair_atributos(
            relato["texto"],
            base["atributos"],
        )

        associacoes = analisar_associacoes(
            conceitos,
            atributos,
            base["associacoes"],
        )

        condicoes = agrupar_por_condicao(associacoes)

        exibir_resultado(
            relato,
            conceitos,
            atributos,
            condicoes,
            indice_conceitos,
        )


if __name__ == "__main__":
    main()
