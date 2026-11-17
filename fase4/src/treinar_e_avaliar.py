"""
Treina CNN do zero e VGG16 (Transfer Learning), avalia no teste e grava evidências.

Uso (raiz do repo, após baixar + preprocessar):
    python fase4/src/treinar_e_avaliar.py
    python fase4/src/treinar_e_avaliar.py --epochs 15 --batch 16
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

SEED = 42
os.environ["PYTHONHASHSEED"] = str(SEED)
random.seed(SEED)
np.random.seed(SEED)

FASE4 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FASE4 / "src"))

from pipeline_imagens import (  # noqa: E402
    CLASSES,
    ConfigPipeline,
    gerar_geradores_keras,
    materializar_processado,
)


def _garantir_tf():
    import tensorflow as tf

    tf.random.set_seed(SEED)
    return tf


def construir_cnn_simples(keras, n_classes: int = 4):
    layers = keras.layers
    modelo = keras.Sequential(
        [
            layers.Input(shape=(224, 224, 3)),
            layers.Conv2D(32, 3, activation="relu", padding="same"),
            layers.MaxPooling2D(),
            layers.Conv2D(64, 3, activation="relu", padding="same"),
            layers.MaxPooling2D(),
            layers.Conv2D(128, 3, activation="relu", padding="same"),
            layers.MaxPooling2D(),
            layers.Conv2D(128, 3, activation="relu", padding="same"),
            layers.MaxPooling2D(),
            layers.Dropout(0.35),
            layers.Flatten(),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.4),
            layers.Dense(n_classes, activation="softmax"),
        ],
        name="cnn_simples",
    )
    modelo.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return modelo


def construir_vgg16_tl(keras, n_classes: int = 4):
    from tensorflow.keras.applications import VGG16

    layers = keras.layers
    base = VGG16(weights="imagenet", include_top=False, input_shape=(224, 224, 3))
    base.trainable = False
    entradas = keras.Input(shape=(224, 224, 3))
    x = layers.Rescaling(255.0)(entradas)
    x = keras.applications.vgg16.preprocess_input(x)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.35)(x)
    x = layers.Dense(128, activation="relu")(x)
    saidas = layers.Dense(n_classes, activation="softmax")(x)
    modelo = keras.Model(entradas, saidas, name="vgg16_tl")
    modelo.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return modelo, base


def avaliar(modelo, fluxo, nome: str, evidencias: Path) -> dict:
    fluxo.reset()
    probs = modelo.predict(fluxo, verbose=0)
    y_pred = np.argmax(probs, axis=1)
    y_true = fluxo.classes
    labels = list(CLASSES)

    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred)
    relatorio = classification_report(y_true, y_pred, target_names=labels, zero_division=0)

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        ax=ax,
    )
    ax.set_xlabel("Previsto")
    ax.set_ylabel("Real")
    ax.set_title(f"Matriz de confusão — {nome}")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    fig_path = evidencias / f"cm_{nome.lower().replace(' ', '_')}.png"
    fig.savefig(fig_path, dpi=140)
    plt.close(fig)

    return {
        "modelo": nome,
        "acuracia": float(acc),
        "precisao_macro": float(prec),
        "recall_macro": float(rec),
        "f1_macro": float(f1),
        "matriz_confusao": cm.tolist(),
        "relatorio": relatorio,
        "figura": str(fig_path),
    }


def plot_curvas(hist_cnn, hist_vgg, hist_ft, evidencias: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(hist_cnn.history["accuracy"], label="treino")
    axes[0].plot(hist_cnn.history["val_accuracy"], label="val")
    axes[0].set_title("CNN simples — acurácia")
    axes[0].legend()
    axes[1].plot(hist_vgg.history["accuracy"], label="treino (cabeça)")
    axes[1].plot(hist_vgg.history["val_accuracy"], label="val (cabeça)")
    if hist_ft is not None:
        offset = len(hist_vgg.history["accuracy"])
        xs = list(range(offset, offset + len(hist_ft.history["accuracy"])))
        axes[1].plot(xs, hist_ft.history["accuracy"], label="treino (fine-tune)")
        axes[1].plot(xs, hist_ft.history["val_accuracy"], label="val (fine-tune)")
    axes[1].set_title("VGG16 TL — acurácia")
    axes[1].legend()
    plt.tight_layout()
    fig.savefig(evidencias / "curvas_treino.png", dpi=140)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--epochs-ft", type=int, default=8)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--pular-download", action="store_true")
    args = parser.parse_args()

    tf = _garantir_tf()
    keras = tf.keras
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

    origem = FASE4 / "data" / "imagens_ecg_completo"
    processado = FASE4 / "data" / "processado"
    models = FASE4 / "models"
    evidencias = FASE4 / "docs" / "evidencias"
    models.mkdir(parents=True, exist_ok=True)
    evidencias.mkdir(parents=True, exist_ok=True)

    n_jpg = sum(1 for _ in origem.rglob("*.jpg")) if origem.exists() else 0
    if n_jpg < 900 and not args.pular_download:
        sys.path.insert(0, str(FASE4 / "data"))
        from baixar_ecg_mendeley import baixar_dataset

        baixar_dataset(origem)

    if not (processado / "manifesto_split.csv").exists():
        materializar_processado(ConfigPipeline(origem=origem, destino=processado))

    fluxo_treino, fluxo_val, fluxo_teste = gerar_geradores_keras(
        processado, batch_size=args.batch, seed=SEED, aumentar_treino=True
    )
    print("amostras:", fluxo_treino.samples, fluxo_val.samples, fluxo_teste.samples)
    print("GPU:", tf.config.list_physical_devices("GPU"))

    # --- CNN ---
    cnn = construir_cnn_simples(keras)
    hist_cnn = cnn.fit(
        fluxo_treino,
        validation_data=fluxo_val,
        epochs=args.epochs,
        callbacks=[
            EarlyStopping(monitor="val_accuracy", patience=6, restore_best_weights=True),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6),
            ModelCheckpoint(
                str(models / "cnn_simples.keras"),
                monitor="val_accuracy",
                save_best_only=True,
            ),
        ],
    )
    cnn.save(models / "cnn_simples_final.keras")

    # --- VGG16 ---
    vgg, base = construir_vgg16_tl(keras)
    hist_vgg = vgg.fit(
        fluxo_treino,
        validation_data=fluxo_val,
        epochs=args.epochs,
        callbacks=[
            EarlyStopping(monitor="val_accuracy", patience=6, restore_best_weights=True),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6),
            ModelCheckpoint(
                str(models / "vgg16_tl.keras"),
                monitor="val_accuracy",
                save_best_only=True,
            ),
        ],
    )

    base.trainable = True
    for camada in base.layers[:-4]:
        camada.trainable = False
    vgg.compile(
        optimizer=keras.optimizers.Adam(1e-5),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    hist_ft = vgg.fit(
        fluxo_treino,
        validation_data=fluxo_val,
        epochs=args.epochs_ft,
        callbacks=[
            EarlyStopping(monitor="val_accuracy", patience=4, restore_best_weights=True),
            ModelCheckpoint(
                str(models / "vgg16_tl.keras"),
                monitor="val_accuracy",
                save_best_only=True,
            ),
        ],
    )
    vgg.save(models / "vgg16_tl_final.keras")

    cnn_eval = (
        keras.models.load_model(models / "cnn_simples.keras")
        if (models / "cnn_simples.keras").exists()
        else cnn
    )
    vgg_eval = (
        keras.models.load_model(models / "vgg16_tl.keras")
        if (models / "vgg16_tl.keras").exists()
        else vgg
    )

    m_cnn = avaliar(cnn_eval, fluxo_teste, "CNN_simples", evidencias)
    m_vgg = avaliar(vgg_eval, fluxo_teste, "VGG16_TL", evidencias)
    plot_curvas(hist_cnn, hist_vgg, hist_ft, evidencias)

    comparativo = pd.DataFrame(
        [
            {k: m_cnn[k] for k in ["modelo", "acuracia", "precisao_macro", "recall_macro", "f1_macro"]},
            {k: m_vgg[k] for k in ["modelo", "acuracia", "precisao_macro", "recall_macro", "f1_macro"]},
        ]
    )
    print(comparativo.to_string(index=False))
    melhor_nome = comparativo.loc[comparativo["f1_macro"].idxmax(), "modelo"]
    melhor = cnn_eval if str(melhor_nome).startswith("CNN") else vgg_eval
    melhor.save(models / "melhor_modelo.keras")

    # Figura-resumo tipo "print de métricas"
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.axis("off")
    tabela = comparativo.round(3)
    ax.table(
        cellText=tabela.values,
        colLabels=tabela.columns,
        loc="center",
        cellLoc="center",
    )
    ax.set_title("Métricas no conjunto de teste (seed=42)")
    fig.savefig(evidencias / "tabela_metricas.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    payload = {
        "aviso_clinico": "Protótipo acadêmico — NÃO substitui avaliação médica.",
        "seed": SEED,
        "melhor_modelo": str(melhor_nome),
        "cnn_simples": {k: v for k, v in m_cnn.items() if k != "figura"},
        "vgg16_tl": {k: v for k, v in m_vgg.items() if k != "figura"},
    }
    (evidencias / "metricas_teste.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Melhor modelo:", melhor_nome)
    print("Evidências em", evidencias)


if __name__ == "__main__":
    main()
