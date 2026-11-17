"""
Pipeline de preparação de imagens de ECG para a Fase 4.

- Redimensiona para 224×224 (compatível com VGG16)
- Normaliza para [0, 1]
- Garante 3 canais RGB
- Split estratificado 70% / 15% / 15% com seed 42
- Copia (ou regrava) imagens processadas em pastas treino|validacao|teste
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

SEED = 42
TAMANHO_ALVO = (224, 224)  # (largura, altura) no OpenCV
FRACAO_TREINO = 0.70
FRACAO_VAL = 0.15
FRACAO_TESTE = 0.15

CLASSES = (
    "Normal",
    "Infarto_Miocardio",
    "Historico_Infarto_Miocardio",
    "Batimento_Anormal",
)

PARTICOES = ("treino", "validacao", "teste")


@dataclass
class ConfigPipeline:
    origem: Path
    destino: Path
    tamanho: tuple[int, int] = TAMANHO_ALVO
    seed: int = SEED
    fracao_treino: float = FRACAO_TREINO
    fracao_val: float = FRACAO_VAL
    fracao_teste: float = FRACAO_TESTE


def listar_imagens(origem: Path) -> pd.DataFrame:
    """Lista JPGs por classe a partir da pasta bruta organizada."""
    linhas = []
    for classe in CLASSES:
        pasta = origem / classe
        if not pasta.is_dir():
            continue
        for caminho in sorted(pasta.glob("*.jpg")):
            linhas.append(
                {
                    "caminho": str(caminho.resolve()),
                    "arquivo": caminho.name,
                    "classe": classe,
                }
            )
    if not linhas:
        raise FileNotFoundError(
            f"Nenhuma imagem encontrada em {origem}. "
            "Execute: python fase4/data/baixar_ecg_mendeley.py"
        )
    df = pd.DataFrame(linhas)
    return df


def carregar_e_preprocessar(
    caminho: str | Path,
    tamanho: tuple[int, int] = TAMANHO_ALVO,
) -> np.ndarray:
    """
    Lê uma imagem, converte para RGB, redimensiona e normaliza para [0, 1].

    Retorna array float32 com shape (H, W, 3).
    """
    caminho = Path(caminho)
    bgr = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Falha ao ler imagem: {caminho}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    redim = cv2.resize(rgb, tamanho, interpolation=cv2.INTER_AREA)
    return (redim.astype(np.float32) / 255.0)


def split_estratificado(
    df: pd.DataFrame,
    seed: int = SEED,
    fracao_treino: float = FRACAO_TREINO,
    fracao_val: float = FRACAO_VAL,
    fracao_teste: float = FRACAO_TESTE,
) -> pd.DataFrame:
    """Atribui particao ∈ {treino, validacao, teste} de forma estratificada."""
    if abs(fracao_treino + fracao_val + fracao_teste - 1.0) > 1e-6:
        raise ValueError("Frações de split devem somar 1.0")

    treino_val, teste = train_test_split(
        df,
        test_size=fracao_teste,
        random_state=seed,
        stratify=df["classe"],
    )
    # Do restante, a validação é fracao_val / (treino+val)
    fracao_val_relativa = fracao_val / (fracao_treino + fracao_val)
    treino, validacao = train_test_split(
        treino_val,
        test_size=fracao_val_relativa,
        random_state=seed,
        stratify=treino_val["classe"],
    )

    out = df.copy()
    out["particao"] = ""
    out.loc[treino.index, "particao"] = "treino"
    out.loc[validacao.index, "particao"] = "validacao"
    out.loc[teste.index, "particao"] = "teste"
    return out


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def materializar_processado(cfg: ConfigPipeline) -> pd.DataFrame:
    """
    Pré-processa e grava JPGs (uint8) nas pastas destino/particao/classe.
    Também salva manifesto CSV/JSON do split.
    """
    df = listar_imagens(cfg.origem)
    df = split_estratificado(
        df,
        seed=cfg.seed,
        fracao_treino=cfg.fracao_treino,
        fracao_val=cfg.fracao_val,
        fracao_teste=cfg.fracao_teste,
    )

    if cfg.destino.exists():
        shutil.rmtree(cfg.destino)
    cfg.destino.mkdir(parents=True, exist_ok=True)

    registros = []
    for _, row in df.iterrows():
        arr = carregar_e_preprocessar(row["caminho"], tamanho=cfg.tamanho)
        uint8 = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
        bgr = cv2.cvtColor(uint8, cv2.COLOR_RGB2BGR)

        pasta_saida = cfg.destino / row["particao"] / row["classe"]
        pasta_saida.mkdir(parents=True, exist_ok=True)
        saida = pasta_saida / row["arquivo"]
        ok = cv2.imwrite(str(saida), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not ok:
            raise RuntimeError(f"Falha ao gravar {saida}")

        raw = saida.read_bytes()
        registros.append(
            {
                "arquivo": row["arquivo"],
                "classe": row["classe"],
                "particao": row["particao"],
                "origem": row["caminho"],
                "processado": str(saida.resolve()),
                "largura": cfg.tamanho[0],
                "altura": cfg.tamanho[1],
                "bytes": len(raw),
                "sha256": _sha256_bytes(raw),
            }
        )

    manifesto = pd.DataFrame(registros)
    csv_path = cfg.destino / "manifesto_split.csv"
    json_path = cfg.destino / "manifesto_split.json"
    manifesto.to_csv(csv_path, index=False)

    resumo = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "seed": cfg.seed,
        "tamanho": {"largura": cfg.tamanho[0], "altura": cfg.tamanho[1]},
        "fracoes": {
            "treino": cfg.fracao_treino,
            "validacao": cfg.fracao_val,
            "teste": cfg.fracao_teste,
        },
        "totais": {
            "geral": int(len(manifesto)),
            "por_particao": manifesto.groupby("particao").size().to_dict(),
            "por_classe": manifesto.groupby("classe").size().to_dict(),
            "cruzado": (
                manifesto.groupby(["particao", "classe"]).size().unstack(fill_value=0).to_dict()
            ),
        },
        "arquivos": registros,
    }
    json_path.write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifesto


def gerar_geradores_keras(
    destino_processado: Path,
    batch_size: int = 32,
    seed: int = SEED,
    aumentar_treino: bool = True,
):
    """
    Cria ImageDataGenerators Keras a partir das pastas processadas.

    Augmentation (só treino): rotação leve, zoom e variação de brilho.
    Sem flip horizontal (laudo de 12 derivações — espelhar distorce a anatomia do traçado).
    """
    from tensorflow.keras.preprocessing.image import ImageDataGenerator

    kwargs_comum = {
        "rescale": 1.0 / 255.0,
    }

    if aumentar_treino:
        gen_treino = ImageDataGenerator(
            **kwargs_comum,
            rotation_range=8,
            zoom_range=0.1,
            brightness_range=(0.9, 1.1),
            fill_mode="nearest",
        )
    else:
        gen_treino = ImageDataGenerator(**kwargs_comum)

    gen_eval = ImageDataGenerator(**kwargs_comum)

    fluxo_treino = gen_treino.flow_from_directory(
        destino_processado / "treino",
        target_size=(TAMANHO_ALVO[1], TAMANHO_ALVO[0]),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=True,
        seed=seed,
        classes=list(CLASSES),
    )
    fluxo_val = gen_eval.flow_from_directory(
        destino_processado / "validacao",
        target_size=(TAMANHO_ALVO[1], TAMANHO_ALVO[0]),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=False,
        classes=list(CLASSES),
    )
    fluxo_teste = gen_eval.flow_from_directory(
        destino_processado / "teste",
        target_size=(TAMANHO_ALVO[1], TAMANHO_ALVO[0]),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=False,
        classes=list(CLASSES),
    )
    return fluxo_treino, fluxo_val, fluxo_teste


def main() -> None:
    import argparse

    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Pré-processa ECGs da Fase 4.")
    parser.add_argument(
        "--origem",
        type=Path,
        default=raiz / "data" / "imagens_ecg_completo",
    )
    parser.add_argument(
        "--destino",
        type=Path,
        default=raiz / "data" / "processado",
    )
    args = parser.parse_args()
    cfg = ConfigPipeline(origem=args.origem, destino=args.destino)
    manifesto = materializar_processado(cfg)
    print(manifesto.groupby(["particao", "classe"]).size())
    print(f"Manifesto em {cfg.destino / 'manifesto_split.csv'}")


if __name__ == "__main__":
    main()
