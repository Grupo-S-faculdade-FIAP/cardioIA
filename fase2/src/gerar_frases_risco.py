"""Gera fase2/data/frases_risco.csv — frases manuais + templates da base (SDD Fase 2, §4).

    python fase2/src/gerar_frases_risco.py

- As frases manuais (fase2/data/frases_manuais.csv) entram como estão; todo o
  conjunto de teste vem delas.
- Os templates combinam expressões da knowledge_base com sinais de alarme
  (alto risco) ou com contextos leves/estáveis, queixas não cardíacas e
  negações (baixo risco). Rótulo e critério vêm do próprio template (§4.1).
  Templates vão só para o treino.
- Seed fixa: o arquivo é reprodutível e um teste confere a sincronia.
"""

import csv
import random
import sys
from itertools import product

from carregador_base import carregar_base_conhecimento
from contrato_dataset import ARQUIVO_DATASET
from extrator_sintomas import normalizar_texto

SEED = 42
ARQUIVO_MANUAIS = ARQUIVO_DATASET.parent / "frases_manuais.csv"
COLUNAS = ["frase", "situacao", "origem", "particao", "criterio"]
QUANTIDADE_POR_CRITERIO = {"A1": 45, "A2": 15, "A3": 15, "A4": 15, "B1": 35, "B2": 35, "B3": 20}

# Itens em tupla têm forma masculina e feminina; as duas entram nas combinações.
ABERTURAS_DOR = ["Estou com", "Sinto", "Senti", "Comecei a sentir", "Tenho", "Hoje senti", "Agora estou com"]
SINAIS_COM_DOR = [
    "que vai para o braço", "que vai para o ombro", "que vai para a mandíbula",
    "que sobe para o pescoço", "que vai para as costas", "que chega na boca do estômago",
    "há mais de vinte minutos", "que não melhorou", "que não passa com repouso",
    "que começou de repente", ("mesmo estando parado", "mesmo estando parada"), "em repouso",
    "e comecei a suar frio", "com suor frio", "e sinto enjoo", "com vontade de vomitar",
    ("e fiquei tonto", "e fiquei tonta"), "e quase desmaiei", "com falta de ar",
    "que está cada vez mais forte", "que agora vem com menos esforço", "acontecendo mais vezes",
]
PREFIXOS_DESMAIO = ["", "Hoje ", "Ontem ", "Do nada "]
CIRCUNSTANCIAS_DESMAIO = [
    "enquanto caminhava", "no trabalho", "ao levantar da cama", "e bati a cabeça",
    "sem nenhum aviso", "dentro do ônibus", "depois do almoço", "na fila do mercado",
    "enquanto tomava banho", "no meio da aula",
]
DISPNEIA_EM_REPOUSO_OU_SUBITA = [
    "Estou com falta de ar em repouso", "Fiquei com falta de ar de repente",
    "Comecei de repente a ficar sem ar",
    ("Tenho dificuldade para respirar mesmo estando parado", "Tenho dificuldade para respirar mesmo estando parada"),
]
TEMPOS_DISPNEIA_AGUDA = ["desde ontem", "hoje", "agora há pouco", "desde cedo", "há algumas horas"]
DISPNEIA_NOTURNA = [
    "Acordo de madrugada com falta de ar", "Acordo à noite com falta de ar",
    "A falta de ar me acorda", "Acordo sem conseguir respirar",
]
TEMPOS_DISPNEIA_NOTURNA = ["todas as noites", "nesta semana", "há três noites", "desde sábado"]
ATIPICOS = [
    "Comecei a suar frio e sentir enjoo", "Estou com suor frio e náusea",
    "Senti suor frio e vontade de vomitar", "Estou suando muito e com enjoo",
    ("De repente fiquei muito cansado e com mal-estar", "De repente fiquei muito cansada e com mal-estar"),
]
CONTEXTOS_ATIPICOS = ["sem dor no peito", "depois do almoço", "desde cedo", "agora há pouco", "enquanto descansava"]

SINTOMAS_LEVES = [
    ("Fico um pouco cansado", "Fico um pouco cansada"), "Sinto um cansaço leve",
    "Tenho uma falta de ar leve", "Fico com um pouco de falta de ar",
    "Sinto as pernas um pouco pesadas", "Tenho um leve cansaço",
]
GATILHOS_LEVES = [
    "quando subo escadas", "depois de caminhar bastante", "no fim do dia",
    "depois de um dia cheio", "quando corro", "quando carrego peso",
]
TEMPOS_ESTAVEIS = ["há meses", "há anos", "faz muito tempo", "sempre do mesmo jeito"]
ESFORCOS_ANGINA_ESTAVEL = ["quando subo escadas", "quando caminho rápido", "quando faço esforço"]
QUEIXAS_NAO_CARDIACAS = [
    "Estou com dor de cabeça leve", "Tenho dor nas costas", "Sinto dor no joelho",
    "Estou com coriza", "Tenho dor de garganta", "Sinto azia depois de comer",
    "Estou com dor muscular na coxa", "Tenho tosse com catarro", "Estou com dor de dente",
    "Tenho dor no pé", "Estou com o nariz entupido", "Tenho uma alergia na pele",
    "Estou com o intestino preso", "Tenho dor no pescoço por causa do travesseiro",
    "Estou com o olho coçando", "Tenho uma afta na boca", "Sinto dor no punho",
]
TEMPOS_NAO_CARDIACOS = ["há dois dias", "desde ontem", "de vez em quando", "desde a semana passada", "hoje de manhã"]
NEGACOES = [
    "Não sinto dor no peito", "Não tenho falta de ar", "Nunca desmaiei",
    "Não tenho dor no peito nem falta de ar", "Sem dor no peito", "Não sinto aperto no peito",
]
QUEIXAS_LEVES_APOS_NEGACAO = [
    "só sinto um cansaço leve no fim do dia", "só tenho uma dor de cabeça fraca",
    "só estou com um pouco de tosse", "só tenho uma dor nas costas",
    "só estou com o nariz entupido", "só sinto o estômago pesado",
]


def _expandir(itens):
    """Abre as tuplas (masculino, feminino) em itens separados."""
    return [forma for item in itens for forma in (item if isinstance(item, tuple) else (item,))]


def _frases(formato, *partes):
    return [formato.format(*combinacao) for combinacao in product(*(_expandir(p) for p in partes))]


def _expressoes(base, conceito_id):
    return [e["expressao"] for e in base["expressoes"] if e["conceito_id"] == conceito_id]


def candidatos_por_criterio(base):
    """Todas as frases possíveis de cada critério, em ordem determinística."""
    dores = _expressoes(base, "S013")
    desmaios = _expressoes(base, "S018")

    return {
        "A1": _frases("{} {} {}.", ABERTURAS_DOR, dores, SINAIS_COM_DOR),
        "A2": [
            frase[0].upper() + frase[1:]
            for frase in _frases("{}{} {}.", PREFIXOS_DESMAIO, desmaios, CIRCUNSTANCIAS_DESMAIO)
        ],
        "A3": _frases("{} {}.", DISPNEIA_EM_REPOUSO_OU_SUBITA, TEMPOS_DISPNEIA_AGUDA)
        + _frases("{} {}.", DISPNEIA_NOTURNA, TEMPOS_DISPNEIA_NOTURNA),
        "A4": _frases("{}, {}.", ATIPICOS, CONTEXTOS_ATIPICOS),
        "B1": _frases("{} {} {}.", SINTOMAS_LEVES, GATILHOS_LEVES, TEMPOS_ESTAVEIS)
        + _frases("Sinto {} {} e melhora quando descanso, {}.", dores, ESFORCOS_ANGINA_ESTAVEL, TEMPOS_ESTAVEIS),
        "B2": _frases("{} {}.", QUEIXAS_NAO_CARDIACAS, TEMPOS_NAO_CARDIACOS),
        "B3": _frases("{}, {}.", NEGACOES, QUEIXAS_LEVES_APOS_NEGACAO),
    }


def carregar_frases_manuais(caminho=ARQUIVO_MANUAIS):
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def gerar_dataset(base, manuais=None):
    """Frases manuais seguidas dos templates sorteados (sem duplicata após normalização)."""
    manuais = carregar_frases_manuais() if manuais is None else manuais
    linhas = [
        {
            "frase": item["frase"],
            "situacao": item["situacao"],
            "origem": "manual",
            "particao": item["particao"],
            "criterio": item["criterio"],
        }
        for item in manuais
    ]
    vistas = {normalizar_texto(linha["frase"]) for linha in linhas}
    sorteio = random.Random(SEED)

    for criterio, candidatos in candidatos_por_criterio(base).items():
        sorteio.shuffle(candidatos)
        escolhidas = 0
        for frase in candidatos:
            chave = normalizar_texto(frase)
            if chave in vistas:
                continue
            vistas.add(chave)
            linhas.append({
                "frase": frase,
                "situacao": "alto risco" if criterio.startswith("A") else "baixo risco",
                "origem": "template",
                "particao": "treino",
                "criterio": criterio,
            })
            escolhidas += 1
            if escolhidas == QUANTIDADE_POR_CRITERIO[criterio]:
                break

    return linhas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    linhas = gerar_dataset(carregar_base_conhecimento())

    with ARQUIVO_DATASET.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)

    templates = sum(linha["origem"] == "template" for linha in linhas)
    print(f"{len(linhas)} frases ({len(linhas) - templates} manuais, {templates} templates) em {ARQUIVO_DATASET}")


if __name__ == "__main__":
    main()
