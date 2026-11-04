#!/usr/bin/env python3
"""Gera os PDFs dos relatórios da Fase 3 a partir dos .md (pandoc + Edge/Chrome em modo headless).

Os .pdf são exportações dos .md: regenerar sempre que o texto ou as evidências (prints) mudarem.

Uso (de qualquer pasta):
    python fase3/docs/gerar_pdfs.py          # os dois relatórios
    python fase3/docs/gerar_pdfs.py edge     # só o relatório da Parte 1
    python fase3/docs/gerar_pdfs.py mqtt     # só o relatório da Parte 2

Requisitos: pandoc no PATH e Microsoft Edge ou Google Chrome (ou aponte o executável na
variável de ambiente NAVEGADOR). Opcional: pymupdf, para conferir páginas e imagens do PDF.

O script também confere o mínimo de páginas exigido pelo enunciado da Fase 3 (Parte 1: 1 página;
Parte 2: 2 páginas) e acusa relatório sem nenhuma imagem de evidência.
"""
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DOCS = Path(__file__).resolve().parent
RAIZ = DOCS.parent.parent
REPO_URL = "https://github.com/Grupo-S-faculdade-FIAP/cardioIA"

# chave -> (nome do arquivo sem extensão, mínimo de páginas do enunciado)
RELATORIOS = {
    "edge": ("relatorio_edge", 1),
    "mqtt": ("relatorio_mqtt", 2),
}

CSS = """
@page { size: A4; margin: 17mm 16mm 19mm 16mm; }
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
html { font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt;
       color: #1a1a1a; line-height: 1.45; }
body { margin: 0; max-width: none; padding: 0; }
h1 { font-size: 20pt; margin: 0 0 4pt; }
h2 { font-size: 15pt; color: #14407a; margin: 0 0 10pt; }
h3 { font-size: 12pt; color: #14407a; margin: 16pt 0 6pt; break-after: avoid; }
h4 { font-size: 11pt; color: #14407a; margin: 12pt 0 4pt; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
a { color: #14407a; text-decoration: none; }
code, pre { font-family: Consolas, "DejaVu Sans Mono", monospace; font-size: 9pt; }
code { background: #f2f2f2; padding: 1px 3px; border-radius: 3px; }
pre { background: #f5f5f5; padding: 8pt 10pt; border-radius: 4px; white-space: pre-wrap;
      break-inside: avoid; }
pre code { background: none; padding: 0; }
blockquote { background: #fdf2f1; border-left: 4px solid #bf382a; margin: 8pt 0; padding: 6pt 12pt; }
blockquote p { margin: 2pt 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 9.5pt; }
th, td { border: 1px solid #b4b4b4; padding: 4pt 6pt; vertical-align: top; text-align: left; }
th { background: #edf1f6; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
img { max-width: 100%; height: auto; }
p:has(> img:only-child) { break-inside: avoid; break-after: avoid; margin-bottom: 2pt; text-align: center; }
p > img:only-child { border: 1px solid #b4b4b4; max-height: 100mm; width: auto; }
/* capturas do dashboard (retrato, recortadas ao card): mais altura para o texto ficar legivel */
p > img[alt^="Dashboard"] { max-height: 150mm; }
p:has(> em:only-child) { font-size: 9.5pt; color: #444; text-align: center; margin-top: 2pt; }
"""

PADRAO_LINK = re.compile(r'href="([^"]*)"')


def achar_navegador() -> str:
    """Devolve o executável do Edge ou do Chrome."""
    candidatos = [
        os.environ.get("NAVEGADOR"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for nome in ("microsoft-edge", "msedge", "google-chrome", "chromium", "chromium-browser", "chrome"):
        candidatos.append(shutil.which(nome))
    for c in candidatos:
        if c and Path(c).exists():
            return c
    sys.exit("Não achei Edge nem Chrome. Instale um deles ou defina NAVEGADOR com o caminho do executável.")


def reescrever_links_relativos(conteudo: str, pasta_do_md: Path) -> str:
    """Troca links relativos (ex.: contrato_mqtt.md) por URLs do GitHub, que funcionam dentro do PDF."""

    def trocar(m: re.Match) -> str:
        alvo = html.unescape(m.group(1))
        if not alvo or re.match(r"^([a-z][a-z0-9+.-]*:|#|data:)", alvo, re.I):
            return m.group(0)
        caminho, _, ancora = alvo.partition("#")
        destino = (pasta_do_md / caminho).resolve()
        if not destino.exists():
            print(f"  aviso: link relativo sem destino: {alvo}")
            return m.group(0)
        tipo = "tree" if destino.is_dir() else "blob"
        url = f"{REPO_URL}/{tipo}/main/{destino.relative_to(RAIZ).as_posix()}"
        return f'href="{url}{"#" + ancora if ancora else ""}"'

    return PADRAO_LINK.sub(trocar, conteudo)


def flag_de_destaque() -> str:
    """O pandoc 3.8 trocou --highlight-style por --syntax-highlighting."""
    saida = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, check=True).stdout
    versao = re.search(r"pandoc(?:\.exe)? (\d+)\.(\d+)", saida)
    novo = bool(versao) and (int(versao.group(1)), int(versao.group(2))) >= (3, 8)
    return "--syntax-highlighting=pygments" if novo else "--highlight-style=pygments"


def md_para_html(md: Path, nome: str, pasta_tmp: Path) -> Path:
    """Converte o .md em um HTML autônomo (CSS e imagens embutidos)."""
    css = pasta_tmp / "estilo.css"
    css.write_text(CSS, encoding="utf-8")
    saida = pasta_tmp / f"{nome}.html"
    subprocess.run(
        [
            "pandoc", "-f", "gfm", "-t", "html5", "-s", "--embed-resources",
            "--resource-path", str(md.parent), "--css", str(css),
            flag_de_destaque(), "--columns=10000", "--wrap=none",
            "-M", "document-css=false", "-M", f"pagetitle=CardioIA Fase 3 - {nome}",
            "-o", str(saida), str(md),
        ],
        check=True,
    )
    saida.write_text(reescrever_links_relativos(saida.read_text(encoding="utf-8"), md.parent), encoding="utf-8")
    return saida


def aguardar_arquivo(arquivo: Path, limite_s: int = 120) -> None:
    """O Edge pode encerrar antes de terminar de gravar o PDF: espera o arquivo aparecer e parar de crescer."""
    fim = time.monotonic() + limite_s
    anterior = -1
    while time.monotonic() < fim:
        if arquivo.exists():
            tamanho = arquivo.stat().st_size
            if tamanho > 0 and tamanho == anterior:
                return
            anterior = tamanho
        time.sleep(1.5)


def html_para_pdf(navegador: str, pagina: Path, pdf: Path, pasta_tmp: Path) -> None:
    """Imprime o HTML em PDF (A4, sem cabeçalho nem rodapé do navegador)."""
    # Um perfil novo por relatório: se um Edge anterior ainda estiver encerrando, ele não trava este
    # e a impressão não é repassada a uma instância antiga (o que deixaria o PDF velho no lugar).
    perfil = pasta_tmp / f"perfil-{pdf.stem}"
    subprocess.run(
        [
            navegador, "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
            f"--user-data-dir={perfil}", f"--print-to-pdf={pdf}", pagina.as_uri(),
        ],
        check=True,
        timeout=180,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    aguardar_arquivo(pdf)


def conferir_pdf(pdf: Path, minimo_paginas: int) -> bool:
    """Confere páginas e imagens do PDF gerado. Devolve False se algo estiver fora do esperado."""
    if not pdf.exists() or pdf.stat().st_size == 0:
        print(f"  ERRO: {pdf.name} não foi gerado")
        return False
    try:
        import pymupdf  # type: ignore
    except ImportError:
        print(f"  {pdf.name}: gerado ({pdf.stat().st_size // 1024} KB); instale pymupdf para conferir páginas e imagens")
        return True
    doc = pymupdf.open(pdf)
    imagens = sum(len(p.get_images()) for p in doc)
    ok = True
    print(f"  {pdf.name}: {doc.page_count} páginas (mínimo do enunciado: {minimo_paginas}), {imagens} imagens, {pdf.stat().st_size // 1024} KB")
    if doc.page_count < minimo_paginas:
        print("  ERRO: menos páginas que o mínimo do enunciado")
        ok = False
    if imagens == 0:
        print("  ERRO: nenhuma imagem de evidência no PDF")
        ok = False
    return ok


def main(argumentos: list[str]) -> int:
    escolhidos = argumentos or list(RELATORIOS)
    desconhecidos = [a for a in escolhidos if a not in RELATORIOS]
    if desconhecidos:
        sys.exit(f"Relatório desconhecido: {desconhecidos}. Use: {', '.join(RELATORIOS)}")
    if not shutil.which("pandoc"):
        sys.exit("pandoc não está no PATH (https://pandoc.org/installing.html)")
    navegador = achar_navegador()

    tudo_certo = True
    # ignore_cleanup_errors: no Windows o Edge pode segurar arquivos do perfil por alguns instantes.
    with tempfile.TemporaryDirectory(prefix="cardioia-pdf-", ignore_cleanup_errors=True) as tmp:
        pasta_tmp = Path(tmp)
        for chave in escolhidos:
            nome, minimo = RELATORIOS[chave]
            print(f"{nome}.md -> {nome}.pdf")
            pagina = md_para_html(DOCS / f"{nome}.md", nome, pasta_tmp)
            # O PDF é gravado primeiro numa pasta temporária: só substitui o do repositório se
            # for novo e passar na conferência (um PDF antigo nunca é validado por engano).
            pdf_novo = pasta_tmp / f"{nome}.pdf"
            html_para_pdf(navegador, pagina, pdf_novo, pasta_tmp)
            if conferir_pdf(pdf_novo, minimo):
                shutil.copyfile(pdf_novo, DOCS / f"{nome}.pdf")
            else:
                print(f"  {nome}.pdf do repositório NÃO foi alterado")
                tudo_certo = False
    return 0 if tudo_certo else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
