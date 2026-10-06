"""Gera o mapa de conhecimento no formato pedido no enunciado da Fase 2.

    sintoma_1,sintoma_2,doenca_associada,...

Cada linha traz duas formas de o paciente relatar o mesmo sintoma e uma
condição associada a ele na base, com o tipo de relação, o peso usado na
pontuação e as fontes. Toda expressão da base aparece em pelo menos uma linha.

É um arquivo DERIVADO dos CSVs normalizados da knowledge_base: edite a base
e rode de novo (SDD Fase 2, §3 regra 12):

    python fase2/src/gerar_mapa_conhecimento.py
"""

import csv
import sys

from analisador_clinico import PESOS_RELACAO
from carregador_base import PASTA_BASE, carregar_base_conhecimento

ARQUIVO_MAPA = PASTA_BASE / "mapa_conhecimento.csv"
COLUNAS_MAPA = [
    "sintoma_1",
    "sintoma_2",
    "doenca_associada",
    "conceito_clinico",
    "tipo_relacao",
    "peso",
    "fontes",
    "associacao_id",
]


def gerar_linhas_mapa(base):
    """Uma linha para cada par de expressões de cada associação (valores em texto)."""
    nomes = {item["conceito_id"]: item["conceito_clinico"] for item in base["conceitos"]}
    variantes_por_conceito = {}
    for item in base["expressoes"]:
        variantes_por_conceito.setdefault(item["conceito_id"], []).append(item["expressao"])

    linhas = []
    for associacao in base["associacoes"]:
        variantes = variantes_por_conceito[associacao["conceito_id"]]

        for posicao in range(0, len(variantes), 2):
            sintoma_1 = variantes[posicao]
            # Com número ímpar de variantes, a última faz par com a primeira.
            sintoma_2 = variantes[posicao + 1] if posicao + 1 < len(variantes) else variantes[0]

            linhas.append({
                "sintoma_1": sintoma_1,
                "sintoma_2": sintoma_2 if sintoma_2 != sintoma_1 else "",
                "doenca_associada": associacao["condicao_associada"],
                "conceito_clinico": nomes[associacao["conceito_id"]],
                "tipo_relacao": associacao["tipo_relacao"],
                "peso": str(PESOS_RELACAO[associacao["tipo_relacao"]]),
                "fontes": associacao["fonte_id"],
                "associacao_id": associacao["associacao_id"],
            })

    return linhas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    linhas = gerar_linhas_mapa(carregar_base_conhecimento())

    # utf-8-sig: o Excel abre os acentos corretamente.
    with ARQUIVO_MAPA.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_MAPA, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)

    print(f"{len(linhas)} linhas gravadas em {ARQUIVO_MAPA}")


if __name__ == "__main__":
    main()
