"""
Baixa o PDF original de cada um dos 3 artigos citados na Parte 2 (Dados
Textuais) e gera uma versão com destaque amarelo (highlight) exatamente nos
trechos que foram usados nos recortes .txt já existentes em
assets/documentos_cientificos/.

Por quê: os .txt são recortes seletivos dos artigos (não o texto integral).
Ter o PDF original com o trecho usado destacado deixa claro, pra quem for
conferir depois, exatamente o que este projeto extraiu de cada fonte —
sem exigir que a pessoa releia o artigo inteiro pra achar o que foi citado.

Método: converte cada frase do recorte em uma string de busca (cortada em
pedaços de até 80 caracteres — strings maiores não casam bem em colunas
justificadas, onde o espaçamento entre palavras varia por linha), procura
essas strings no texto do PDF com pymupdf e adiciona uma anotação de
destaque em cada ocorrência encontrada.

Limitação conhecida: nem toda frase é encontrada (tabelas, texto que quebra
entre páginas, e pequenas diferenças de extração HTML-vs-PDF reduzem a taxa
de acerto pra ~85% nos 3 documentos, ver log impresso). Isso é uma cobertura
de destaque incompleta, não um erro de conteúdo — os .txt continuam sendo a
fonte de verdade do que foi usado.

Uso (a partir da raiz do repositório):
    python src/destacar_documentos_cientificos.py
"""

import re
import sys
import urllib.request
from pathlib import Path

import pymupdf

REPO_ROOT = Path(__file__).parent.parent
PASTA = REPO_ROOT / "assets" / "documentos_cientificos"

DOCUMENTOS = [
    {
        "nome": "diretriz_insuficiencia_cardiaca",
        "url_pdf": "https://www.scielo.br/j/abc/a/XkVKFb4838qXrXSYbmCYM3K/?format=pdf&lang=pt",
    },
    {
        "nome": "consenso_sindrome_cardiorrenal",
        "url_pdf": "https://www.scielo.br/j/abc/a/ppZHhz5H9yytzsfRnzY6Gmv/?format=pdf&lang=pt",
    },
    {
        "nome": "ckm_current_urgent_concept",
        "url_pdf": "https://www.scielo.br/j/jbn/a/jRnTsXdgMSBGV79NcB5BfwD/?format=pdf&lang=en",
    },
]

LIMITE = 80  # trechos de busca mais longos que isso nao casam bem em coluna justificada
MINIMO = 25  # trechos mais curtos que isso dao falso-positivo (casam em qualquer lugar)


def baixar_original(url: str, destino: Path) -> None:
    if not destino.exists():
        print(f"Baixando {destino.name} de {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(destino, "wb") as f:
            f.write(resp.read())


def carregar_trechos(caminho_txt: Path) -> list[str]:
    """Quebra o recorte .txt em pedacos curtos o suficiente pra dar match
    confiavel num PDF de coluna justificada (frase -> virgula -> palavra,
    nessa ordem, so quebrando mais fino quando o pedaco anterior nao coube)."""
    conteudo = caminho_txt.read_text(encoding="utf-8")
    corpo = conteudo.split("=" * 80, 1)
    corpo = corpo[1] if len(corpo) > 1 else conteudo
    paragrafos = [p.strip() for p in corpo.split("\n\n") if p.strip()]

    trechos: list[str] = []
    for p in paragrafos:
        if p.startswith("=") or p.startswith("---") or len(p) < 5:
            continue
        for frase in re.split(r"(?<=[.;])\s+", p):
            frase = frase.strip()
            if len(frase) < MINIMO:
                continue
            if len(frase) <= LIMITE:
                trechos.append(frase)
                continue
            trechos.extend(_quebrar(frase, r"(?<=,)\s+"))
    return trechos


def _quebrar(texto: str, separador_regex: str) -> list[str]:
    partes = re.split(separador_regex, texto)
    resultado: list[str] = []
    buffer = ""
    for parte in partes:
        if len(parte) > LIMITE:
            if len(buffer) >= MINIMO:
                resultado.append(buffer)
            buffer = ""
            resultado.extend(_quebrar(parte, r"\s+"))
            continue
        candidato = f"{buffer} {parte}".strip() if buffer else parte
        if len(candidato) <= LIMITE:
            buffer = candidato
        else:
            if len(buffer) >= MINIMO:
                resultado.append(buffer)
            buffer = parte
    if len(buffer) >= MINIMO:
        resultado.append(buffer)
    return resultado


def destacar(caminho_pdf_entrada: Path, caminho_txt: Path, caminho_pdf_saida: Path) -> None:
    trechos = carregar_trechos(caminho_txt)
    doc = pymupdf.open(caminho_pdf_entrada)
    encontrados = 0
    for trecho in trechos:
        achou = False
        for page in doc:
            for rect in page.search_for(trecho):
                page.add_highlight_annot(rect)
                achou = True
        encontrados += achou
    doc.save(caminho_pdf_saida, garbage=3, deflate=True)
    doc.close()
    pct = 100 * encontrados / len(trechos) if trechos else 0
    print(f"{caminho_pdf_saida.name}: {encontrados}/{len(trechos)} trechos encontrados e destacados ({pct:.1f}%)")


def main() -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    for doc_info in DOCUMENTOS:
        nome = doc_info["nome"]
        pdf_original = PASTA / f"{nome}_original.pdf"
        txt = PASTA / f"{nome}.txt"
        pdf_saida = PASTA / f"{nome}_destacado.pdf"

        baixar_original(doc_info["url_pdf"], pdf_original)
        if not txt.exists():
            print(f"AVISO: {txt.name} não existe — pulando (o recorte .txt precisa ser criado manualmente antes)")
            continue
        destacar(pdf_original, txt, pdf_saida)


if __name__ == "__main__":
    main()
