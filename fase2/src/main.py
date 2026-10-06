"""Ponto de entrada da Parte 1 do CardioIA.

Uso:
    python fase2/src/main.py                       # analisa os 10 relatos
    python fase2/src/main.py --texto "Não sinto dor no peito, mas fico sem ar ao deitar"
"""

import argparse
import sys

from analisador_clinico import analisar_relato, criar_indice_conceitos
from carregador_base import carregar_base_conhecimento, carregar_relatos

AVISO_CLINICO = (
    "⚠️ AVISO CLÍNICO: Este sistema é um protótipo acadêmico e NÃO substitui avaliação médica.\n"
    "Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944)."
)


def _nome(indice_conceitos, conceito_id):
    return indice_conceitos[conceito_id]["conceito_clinico"]


def _pontos(valor):
    return f"{valor} ponto" if valor == 1 else f"{valor} pontos"


def _segunda_hipotese(condicoes):
    """2ª colocada com a pontuação; avisa quando ela divide o lugar com outras."""
    if len(condicoes) < 2:
        return "—"
    pontuacao = condicoes[1]["pontuacao_explicativa"]
    empatadas = sum(1 for item in condicoes[1:] if item["pontuacao_explicativa"] == pontuacao)
    texto = f"{condicoes[1]['condicao']} ({pontuacao})"
    return texto + (f" + {empatadas - 1} empatada(s)" if empatadas > 1 else "")


def exibir_resultado(identificador, texto, analise, indice_conceitos):
    """Mostra a análise em formato legível e explicável."""
    print("\n" + "=" * 80)
    print(identificador)
    print("=" * 80)
    print(texto)

    print("\nSINTOMAS IDENTIFICADOS:")
    if not analise["conceitos"]:
        print("- Nenhum conceito cadastrado foi identificado.")
    for item in analise["conceitos"]:
        expressoes = ", ".join(f'"{e}"' for e in item["expressoes_encontradas"])
        print(f"- {item['conceito_id']} | {_nome(indice_conceitos, item['conceito_id'])} ← {expressoes}")

    if analise["conceitos_negados"]:
        print("\nSINTOMAS NEGADOS PELO PACIENTE (não pontuam):")
        for item in analise["conceitos_negados"]:
            expressoes = ", ".join(f'"{e}"' for e in item["expressoes_negadas"])
            print(f"- {item['conceito_id']} | {_nome(indice_conceitos, item['conceito_id'])} ← {expressoes}")

    print("\nCONTEXTO:")
    if not analise["atributos"]:
        print("- Nenhum atributo cadastrado foi identificado.")
    for item in analise["atributos"]:
        print(f"- {item['atributo_id']} | {item['tipo']}: {item['valor']}")

    print("\nHIPÓTESES DA BASE (pontos = peso das evidências + 1 por contexto relevante):")
    if not analise["condicoes"]:
        print("- Nenhuma associação disponível para os conceitos detectados.")
    for posicao, item in enumerate(analise["condicoes"], start=1):
        print(f"{posicao}. {item['condicao']} — {_pontos(item['pontuacao_explicativa'])}")
        evidencias = "; ".join(
            f"{_nome(indice_conceitos, e['conceito_id'])} [{e['tipo_relacao']}, +{e['peso']}]"
            for e in item["evidencias"]
        )
        print(f"   Evidências: {evidencias}")
        if item["atributos"]:
            print(f"   Contextos relevantes: {', '.join(item['atributos'])} (+{len(item['atributos'])})")
        print(f"   Fontes: {', '.join(item['fontes'])}")

    sugestao = analise["sugestao"]
    if sugestao["condicao"]:
        print(f"\n>>> SUGESTÃO PRINCIPAL: {sugestao['condicao']}")
    elif sugestao["empatadas"]:
        print(f"\n>>> INCONCLUSIVO: empate entre {' e '.join(sugestao['empatadas'])}")
    else:
        print("\n>>> SEM SUGESTÃO: nenhum sintoma da base foi identificado.")


def exibir_resumo(linhas):
    """Tabela final: um relato por linha."""
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    print(f"{'Relato':<11}{'Sugestão principal':<36}{'Pontos':>6}   2ª hipótese (pontos)")
    for identificador, analise in linhas:
        sugestao = analise["sugestao"]
        principal = sugestao["condicao"] or "inconclusivo"
        print(
            f"{identificador:<11}{principal:<36}{sugestao['pontuacao']:>6}   "
            f"{_segunda_hipotese(analise['condicoes'])}"
        )


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--texto", help="analisa um texto livre em vez dos 10 relatos")
    args = parser.parse_args()

    base = carregar_base_conhecimento()
    indice_conceitos = criar_indice_conceitos(base["conceitos"])

    if args.texto:
        exibir_resultado("TEXTO INFORMADO", args.texto, analisar_relato(args.texto, base), indice_conceitos)
    else:
        relatos = carregar_relatos()
        print(f"CardioIA: {len(relatos)} relatos carregados.")
        linhas = []
        for relato in relatos:
            analise = analisar_relato(relato["texto"], base)
            exibir_resultado(relato["id"], relato["texto"], analise, indice_conceitos)
            linhas.append((relato["id"], analise))
        exibir_resumo(linhas)

    print("\n" + AVISO_CLINICO)


if __name__ == "__main__":
    main()
