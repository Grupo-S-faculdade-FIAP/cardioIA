"""Classificador de risco por regras (SDD Fase 2, §4.1) — linha de base explicável.

Aplica os critérios de alarme A1–A4 sobre a saída do extrator da Parte 1
(que já descarta sintomas negados). Serve para comparar com o modelo de ML e
para conferir se os rótulos dos templates seguem o critério documentado.
"""

from extrator_sintomas import extrair_atributos, extrair_conceitos

ALTO = "alto risco"
BAIXO = "baixo risco"

DOR_TORACICA = "S013"
DISPNEIA = "S001"
DISPNEIA_NOTURNA = "S003"
FADIGA = "S004"
SUDORESE = "S014"
NAUSEA = "S015"
SINCOPE = "S018"

INICIO_SUBITO = "A009"
REPOUSO = "A005"

# A1: o que, junto com dor torácica, vira sinal de alarme.
CONCEITOS_DE_ALARME_COM_DOR = {DISPNEIA, SUDORESE, NAUSEA, "S016", "S017", SINCOPE}
ATRIBUTOS_DE_ALARME_COM_DOR = {
    REPOUSO, "A007", INICIO_SUBITO, "A011", "A012",
    "A013", "A014", "A015", "A016", "A017", "A018",
    "A021", "A022", "A023",
}


def classificar_por_regras(texto, base):
    """Devolve (situacao, motivos). Sem motivo de alarme, o risco é baixo."""
    conceitos = {c["conceito_id"] for c in extrair_conceitos(texto, base["expressoes"])}
    atributos = {a["atributo_id"] for a in extrair_atributos(texto, base["atributos"])}
    motivos = []

    if DOR_TORACICA in conceitos and (
        conceitos & CONCEITOS_DE_ALARME_COM_DOR or atributos & ATRIBUTOS_DE_ALARME_COM_DOR
    ):
        motivos.append("A1: dor torácica com sinal de alarme")

    if SINCOPE in conceitos:
        motivos.append("A2: síncope")

    if DISPNEIA_NOTURNA in conceitos or (DISPNEIA in conceitos and atributos & {REPOUSO, INICIO_SUBITO}):
        motivos.append("A3: falta de ar em repouso, súbita ou noturna")

    if {SUDORESE, NAUSEA} <= conceitos or (FADIGA in conceitos and INICIO_SUBITO in atributos):
        motivos.append("A4: equivalente atípico")

    return (ALTO if motivos else BAIXO), motivos
