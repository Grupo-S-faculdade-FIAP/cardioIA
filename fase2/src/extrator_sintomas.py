"""Extração de conceitos clínicos e atributos presentes em relatos textuais."""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Negação (SDD Fase 2, §3.1) — versão simplificada do NegEx para PT-BR.
# Um gatilho nega a expressão que começa até JANELA_NEGACAO palavras depois
# dele, desde que os dois estejam na mesma oração.
# ---------------------------------------------------------------------------
GATILHOS_NEGACAO = {"nao", "nem", "sem", "nunca", "jamais", "nenhum", "nenhuma"}
JANELA_NEGACAO = 3

# Só nega a palavra seguinte: "quase desmaiei" é pré-síncope, não síncope.
GATILHOS_NEGACAO_IMEDIATA = {"quase"}

# Locuções que começam com um gatilho mas não negam o que vem depois:
# "fico sem ar quando caminho", "não melhorou e estou suando muito".
PSEUDO_NEGACOES = (
    "nao so", "nao apenas", "nao somente", "nao sei", "nao tenho certeza",
    "nao consigo", "nao aguento", "nao melhora", "nao melhorou", "nao passa",
    "nao passou", "nao para", "nao parou", "nem consigo",
    "sem ar", "sem folego", "sem forcas", "sem querer", "sem tentar",
    "sem conseguir", "sem vontade", "sem motivo", "sem parar", "sem melhora",
    "sem alivio",
)
_PSEUDO_NEGACOES = [tuple(locucao.split()) for locucao in PSEUDO_NEGACOES]

# Pontuação e conjunções encerram o alcance da negação:
# "Não sinto dor no peito, só cansaço" → o cansaço continua afirmado.
SEPARADORES_ORACAO = r"[.,;:!?()\n]"
CONJUNCOES_DE_QUEBRA = {
    "mas", "porem", "contudo", "entretanto", "todavia", "porque", "pois",
    "exceto", "embora", "so", "apenas", "somente",
}


def normalizar_texto(texto):
    """
    Padroniza o texto antes das comparações.

    - converte para minúsculas;
    - remove acentos;
    - remove pontuação;
    - reduz espaços repetidos.

    Isso permite, por exemplo, comparar 'pressão' com 'pressao'.
    """
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return " ".join(texto.split())


def expressao_no_texto(expressao, texto_normalizado):
    """
    Procura uma expressão completa no texto.

    As bordas de palavra evitam que pequenos termos sejam encontrados
    acidentalmente dentro de palavras maiores.
    """
    expressao = normalizar_texto(expressao)

    if not expressao:
        return False

    padrao = rf"(?<!\w){re.escape(expressao)}(?!\w)"
    return re.search(padrao, texto_normalizado) is not None


def tokenizar(texto):
    """
    Devolve as palavras normalizadas do texto e, para cada uma, o número da
    oração em que está. As palavras são as mesmas de normalizar_texto(texto);
    a oração serve apenas para limitar o alcance da negação.
    """
    tokens, oracoes = [], []
    oracao = 0

    for trecho in re.split(SEPARADORES_ORACAO, texto):
        for token in normalizar_texto(trecho).split():
            if token in CONJUNCOES_DE_QUEBRA:
                oracao += 1
            tokens.append(token)
            oracoes.append(oracao)
        oracao += 1

    return tokens, oracoes


def _ocorrencias(expressao, tokens):
    """Posições (início, fim) em que a expressão aparece como sequência de palavras inteiras."""
    alvo = normalizar_texto(expressao).split()
    tamanho = len(alvo)

    if not tamanho:
        return []

    return [
        (inicio, inicio + tamanho)
        for inicio in range(len(tokens) - tamanho + 1)
        if tokens[inicio:inicio + tamanho] == alvo
    ]


def _e_pseudo_negacao(tokens, posicao, inicio_expressao):
    """O gatilho em `posicao` abre uma locução que não nega e termina antes da expressão."""
    for locucao in _PSEUDO_NEGACOES:
        fim = posicao + len(locucao)
        if fim <= inicio_expressao and tuple(tokens[posicao:fim]) == locucao:
            return True
    return False


def _esta_negada(tokens, oracoes, inicio):
    """Verifica se algum gatilho de negação alcança a expressão que começa em `inicio`."""
    anterior = inicio - 1
    if (
        anterior >= 0
        and tokens[anterior] in GATILHOS_NEGACAO_IMEDIATA
        and oracoes[anterior] == oracoes[inicio]
    ):
        return True

    for posicao in range(anterior, max(-1, anterior - JANELA_NEGACAO - 1), -1):
        if oracoes[posicao] != oracoes[inicio]:
            break
        if tokens[posicao] in GATILHOS_NEGACAO and not _e_pseudo_negacao(tokens, posicao, inicio):
            return True

    return False


def localizar_mencoes(texto, termos):
    """
    Encontra cada termo no texto e indica se a menção está negada.

    `termos` é uma lista de pares (chave, expressão). Devolve uma lista de
    dicionários com chave, expressão e a marcação de negação de cada menção.
    """
    tokens, oracoes = tokenizar(texto)
    mencoes = [
        {
            "chave": chave,
            "expressao": expressao,
            "inicio": inicio,
            "fim": fim,
            "negada": _esta_negada(tokens, oracoes, inicio),
        }
        for chave, expressao in termos
        for inicio, fim in _ocorrencias(expressao, tokens)
    ]

    # Expressão contida em outra negada herda a negação:
    # "não acordo de madrugada com falta de ar" nega a DPN e também a dispneia.
    trechos_negados = [(m["inicio"], m["fim"]) for m in mencoes if m["negada"]]
    for mencao in mencoes:
        if not mencao["negada"] and any(
            inicio <= mencao["inicio"] and mencao["fim"] <= fim
            for inicio, fim in trechos_negados
        ):
            mencao["negada"] = True

    return mencoes


def _agrupar_mencoes(mencoes, campo_id, campo_afirmadas, campo_negadas, extras):
    """
    Junta as menções por chave. Um item só é marcado como negado quando
    todas as suas menções estão negadas.
    """
    encontrados = {}

    for mencao in mencoes:
        chave = mencao["chave"]

        if chave not in encontrados:
            encontrados[chave] = {
                campo_id: chave,
                **extras.get(chave, {}),
                campo_afirmadas: [],
                campo_negadas: [],
            }

        destino = campo_negadas if mencao["negada"] else campo_afirmadas
        if mencao["expressao"] not in encontrados[chave][destino]:
            encontrados[chave][destino].append(mencao["expressao"])

    for item in encontrados.values():
        item["negado"] = not item[campo_afirmadas]

    return list(encontrados.values())


def extrair_conceitos(texto, expressoes, incluir_negados=False):
    """
    Identifica conceitos clínicos a partir das expressões cadastradas.

    Conceitos negados pelo paciente ("não sinto dor no peito") são omitidos;
    com incluir_negados=True eles voltam com "negado": True.
    """
    mencoes = localizar_mencoes(
        texto,
        [(item["conceito_id"], item["expressao"]) for item in expressoes],
    )
    conceitos = _agrupar_mencoes(
        mencoes, "conceito_id", "expressoes_encontradas", "expressoes_negadas", {}
    )
    return [c for c in conceitos if incluir_negados or not c["negado"]]


def extrair_atributos(texto, atributos, incluir_negados=False):
    """
    Detecta contexto como esforço, repouso, duração e irradiação.

    Segue a mesma regra de negação dos conceitos: "a dor não melhora quando
    descanso" nega o atributo 'melhora com repouso'.
    """
    termos = [
        (atributo["atributo_id"], gatilho.strip())
        for atributo in atributos
        for gatilho in atributo["expressoes_gatilho"].split("|")
        if gatilho.strip()
    ]
    extras = {
        atributo["atributo_id"]: {
            "tipo": atributo["tipo"],
            "valor": atributo["valor_normalizado"],
        }
        for atributo in atributos
    }
    encontrados = _agrupar_mencoes(
        localizar_mencoes(texto, termos),
        "atributo_id", "gatilhos_encontrados", "gatilhos_negados", extras,
    )
    return [a for a in encontrados if incluir_negados or not a["negado"]]
