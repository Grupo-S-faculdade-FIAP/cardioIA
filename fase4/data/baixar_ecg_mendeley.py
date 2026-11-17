"""
Baixa o dataset completo de ECGs do Mendeley Data (v2) e organiza por classe.

Fonte: Khan, Hussain & Malik — "ECG Images dataset of Cardiac Patients"
DOI: 10.17632/gwbz3fsgp8.2 | Licença: CC BY 4.0

Uso (a partir da raiz do repositório):
    python fase4/data/baixar_ecg_mendeley.py
    python fase4/data/baixar_ecg_mendeley.py --destino fase4/data/imagens_ecg_completo

As ~928 imagens (~615 MB) NÃO entram no Git — ver .gitignore.
A amostra de 120 imagens da Fase 1 permanece em assets/imagens_ecg/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

DATASET_ID = "gwbz3fsgp8"
API_URL = f"https://data.mendeley.com/public-api/datasets/{DATASET_ID}"
USER_AGENT = "CardioIA-FIAP/1.0 (academic; grupo-s)"

# Prefixo do arquivo no Mendeley → pasta no CardioIA (mesmo mapeamento da Fase 1)
MAPA_CLASSES = {
    "Normal": "Normal",
    "MI": "Infarto_Miocardio",
    "PMI": "Historico_Infarto_Miocardio",
    "HB": "Batimento_Anormal",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
DESTINO_PADRAO = Path(__file__).resolve().parent / "imagens_ecg_completo"
MANIFEST_NOME = "_manifest_completo.json"


def _requisicao_json(url: str, tentativas: int = 5) -> dict:
    ultimo_erro: Exception | None = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            ultimo_erro = exc
            espera = 2 ** i
            print(f"  aviso: falha ao consultar API ({exc}); nova tentativa em {espera}s")
            time.sleep(espera)
    raise RuntimeError(f"Não foi possível consultar {url}: {ultimo_erro}")


def _baixar_arquivo(url: str, destino: Path, tentativas: int = 5) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    ultimo_erro: Exception | None = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as resp, open(tmp, "wb") as out:
                while True:
                    bloco = resp.read(1024 * 256)
                    if not bloco:
                        break
                    out.write(bloco)
            tmp.replace(destino)
            return
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            ultimo_erro = exc
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            espera = 2 ** i
            print(f"  aviso: falha em {destino.name} ({exc}); retry em {espera}s")
            time.sleep(espera)
    raise RuntimeError(f"Falha ao baixar {url}: {ultimo_erro}")


def _classe_do_nome(filename: str) -> str:
    prefixo = filename.split("(")[0]
    if prefixo not in MAPA_CLASSES:
        raise ValueError(f"Prefixo de classe desconhecido: {filename!r}")
    return MAPA_CLASSES[prefixo]


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def listar_arquivos_api() -> tuple[dict, list[dict]]:
    meta = _requisicao_json(API_URL)
    arquivos = []
    for item in meta.get("files", []):
        nome = item.get("filename", "")
        if not nome.lower().endswith(".jpg"):
            continue
        detalhes = item.get("content_details") or {}
        arquivos.append(
            {
                "filename": nome,
                "classe": _classe_do_nome(nome),
                "download_url": detalhes["download_url"],
                "sha256_esperado": detalhes.get("sha256_hash"),
                "bytes_esperados": detalhes.get("size") or item.get("size"),
            }
        )
    return meta, arquivos


def _arquivo_ok(caminho: Path, arq: dict, forcar: bool) -> dict | None:
    """Retorna registro de manifesto se o arquivo local já serve; senão None."""
    if forcar or not caminho.exists():
        return None
    tamanho = caminho.stat().st_size
    esperado = arq.get("bytes_esperados")
    # Atalho: se o tamanho bate, confia e calcula hash uma vez (evita redownload).
    if esperado is not None and tamanho != esperado:
        return None
    digest = _sha256(caminho)
    if arq.get("sha256_esperado") and digest != arq["sha256_esperado"]:
        return None
    return {
        "classe": arq["classe"],
        "arquivo": arq["filename"],
        "bytes": tamanho,
        "sha256": digest,
    }


def _processar_um(arq: dict, destino: Path, forcar: bool, indice: int, total: int) -> tuple[str, dict]:
    pasta = destino / arq["classe"]
    caminho = pasta / arq["filename"]
    existente = _arquivo_ok(caminho, arq, forcar)
    if existente is not None:
        return "pulado", existente

    print(f"[{indice}/{total}] {arq['classe']}/{arq['filename']}", flush=True)
    _baixar_arquivo(arq["download_url"], caminho)
    digest = _sha256(caminho)
    if arq.get("sha256_esperado") and digest != arq["sha256_esperado"]:
        caminho.unlink(missing_ok=True)
        raise RuntimeError(
            f"Hash SHA-256 divergente para {arq['filename']}: "
            f"obtido={digest} esperado={arq['sha256_esperado']}"
        )
    return "baixado", {
        "classe": arq["classe"],
        "arquivo": arq["filename"],
        "bytes": caminho.stat().st_size,
        "sha256": digest,
    }


def baixar_dataset(destino: Path, forcar: bool = False, workers: int = 8) -> Path:
    destino = destino.resolve()
    destino.mkdir(parents=True, exist_ok=True)

    print(f"Consultando API Mendeley: {API_URL}", flush=True)
    meta, arquivos = listar_arquivos_api()
    contagem = Counter(a["classe"] for a in arquivos)
    print(f"Dataset: {meta.get('name')!r} | DOI {meta.get('doi', {}).get('id')}", flush=True)
    print(f"Arquivos JPG: {len(arquivos)} | por classe: {dict(contagem)}", flush=True)
    print(f"Workers paralelos: {workers}", flush=True)

    manifesto: list[dict] = []
    baixados = 0
    pulados = 0
    total = len(arquivos)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = {
            pool.submit(_processar_um, arq, destino, forcar, i, total): arq
            for i, arq in enumerate(arquivos, start=1)
        }
        for fut in as_completed(futuros):
            status, registro = fut.result()
            manifesto.append(registro)
            if status == "baixado":
                baixados += 1
            else:
                pulados += 1
            feitos = baixados + pulados
            if feitos % 50 == 0 or feitos == total:
                print(f"  progresso: {feitos}/{total} (novos={baixados}, ok={pulados})", flush=True)

    manifesto_path = destino / MANIFEST_NOME
    payload = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "doi": meta.get("doi", {}).get("id"),
        "licenca": (meta.get("data_licence") or {}).get("short_name"),
        "total": len(manifesto),
        "por_classe": dict(Counter(m["classe"] for m in manifesto)),
        "arquivos": sorted(manifesto, key=lambda m: (m["classe"], m["arquivo"])),
    }
    manifesto_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Concluído: baixados={baixados}, já presentes={pulados}, total={len(manifesto)}", flush=True)
    print(f"Manifesto: {manifesto_path}", flush=True)
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa o dataset Mendeley de ECG (completo).")
    parser.add_argument(
        "--destino",
        type=Path,
        default=DESTINO_PADRAO,
        help=f"Pasta de saída (padrão: {DESTINO_PADRAO})",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Baixa novamente mesmo se o arquivo já existir com hash válido.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Downloads paralelos (padrão: 8).",
    )
    args = parser.parse_args()
    baixar_dataset(args.destino, forcar=args.forcar, workers=args.workers)


if __name__ == "__main__":
    main()
