"""Extração de conceitos clínicos e atributos presentes em relatos textuais."""

import re
import unicodedata


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


def extrair_conceitos(texto, expressoes):
    """Identifica conceitos clínicos a partir das expressões cadastradas."""
    texto_normalizado = normalizar_texto(texto)
    encontrados = {}

    for item in expressoes:
        if expressao_no_texto(item["expressao"], texto_normalizado):
            conceito_id = item["conceito_id"]

            # O dicionário evita repetir o mesmo conceito quando duas
            # expressões equivalentes aparecem no mesmo relato.
            if conceito_id not in encontrados:
                encontrados[conceito_id] = {
                    "conceito_id": conceito_id,
                    "expressoes_encontradas": [],
                }

            encontrados[conceito_id]["expressoes_encontradas"].append(
                item["expressao"]
            )

    return list(encontrados.values())


def extrair_atributos(texto, atributos):
    """Detecta contexto como esforço, repouso, duração e irradiação."""
    texto_normalizado = normalizar_texto(texto)
    encontrados = []

    for atributo in atributos:
        gatilhos = [
            gatilho.strip()
            for gatilho in atributo["expressoes_gatilho"].split("|")
            if gatilho.strip()
        ]

        gatilhos_encontrados = [
            gatilho
            for gatilho in gatilhos
            if expressao_no_texto(gatilho, texto_normalizado)
        ]

        if gatilhos_encontrados:
            encontrados.append({
                "atributo_id": atributo["atributo_id"],
                "tipo": atributo["tipo"],
                "valor": atributo["valor_normalizado"],
                "gatilhos_encontrados": gatilhos_encontrados,
            })

    return encontrados
