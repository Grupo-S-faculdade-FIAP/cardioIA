"""Funções responsáveis por carregar os arquivos usados pelo CardioIA."""

from pathlib import Path
import csv

# A raiz do projeto é calculada a partir da localização deste próprio arquivo.
# Assim, o programa não depende da pasta em que o terminal foi aberto.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_BASE = RAIZ_PROJETO / "knowledge_base"
ARQUIVO_RELATOS = RAIZ_PROJETO / "data" / "relatos_pacientes.txt"


def carregar_csv(nome_arquivo):
    """Lê um CSV da knowledge_base e devolve cada linha como dicionário."""
    caminho = PASTA_BASE / nome_arquivo

    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def carregar_base_conhecimento():
    """Carrega os cinco arquivos da base usados na análise textual."""
    return {
        "conceitos": carregar_csv("conceitos.csv"),
        "expressoes": carregar_csv("expressoes.csv"),
        "atributos": carregar_csv("atributos.csv"),
        "associacoes": carregar_csv("associacoes.csv"),
        "fontes": carregar_csv("fontes.csv"),
    }


def carregar_relatos():
    """
    Lê relatos_pacientes.txt e separa os blocos iniciados por 'RELATO XX'.

    O cabeçalho explicativo do arquivo é ignorado.
    """
    texto = ARQUIVO_RELATOS.read_text(encoding="utf-8")
    relatos = []

    for bloco in texto.split("RELATO ")[1:]:
        linhas = [linha.strip() for linha in bloco.splitlines() if linha.strip()]

        if len(linhas) < 2:
            continue

        numero = linhas[0]
        conteudo = " ".join(linhas[1:])

        relatos.append({
            "id": f"RELATO {numero}",
            "texto": conteudo,
        })

    return relatos
