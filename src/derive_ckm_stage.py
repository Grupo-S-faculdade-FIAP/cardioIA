"""
Deriva as Camadas 2-4 da especificação de estágios CKM
(.spec/especificacao-estagios-ckm.md) a partir do dataset numérico já
processado (data/processed/pns_ckm_rce_2013.csv).

Não baixa nem reprocessa nenhum dado bruto da PNS — todas as colunas usadas
aqui já existem no CSV de origem (ver a matriz de disponibilidade na
especificação). Este script só aplica limiares clínicos e combina colunas
já existentes; por isso vive separado do pipeline de extração
(src/build_pns_ckm_dataset.py), que continua intocado.

IMPORTANTE (ver especificação §6.4): CKM_Stage não é uma probabilidade nem um
diagnóstico confirmado — indica que os valores medidos da pessoa, neste corte
transversal único, ATENDEM AO CRITÉRIO oficial daquele estágio. Uma medição
isolada (ex.: uma HbA1c alterada) não equivale ao protocolo diagnóstico
clínico completo, que tipicamente exige confirmação por segunda medição.

Camada 2 (indicador calculado):
  Categoria_KDIGO_G  — a partir de eGFR_CKD_EPI_2021

Camada 3 (classificadores):
  Obesidade                    — IMC >= 30
  Obesidade_Central             — RCE >= 0,5 (WHtR)
  Classificacao_Glicemica       — Normal / Pre_Diabetes / Diabetes (HbA1c + diagnóstico)
  Hipertensao_CKM               — PAS>=130 ou PAD>=80 ou diagnóstico
  Dislipidemia                  — colesterol total >=200 ou diagnóstico (informativo,
                                   não alimenta o estágio — CKM usa hipertrigliceridemia,
                                   que não existe na PNS, ver especificação §3.C)
  Sindrome_Metabolica_Parcial   — 3 de 4 critérios ATP III disponíveis (falta
                                   triglicerídeos; só calculado com os 4 completos)

Camada 4:
  CKM_Stage ∈ {0, 1, 2, 4, NaN} — estágio 3 é estruturalmente indetectável
  com esta base (sem CAC/NT-proBNP/troponina/ecocardiograma, ver
  especificação §5): quem cai em estágio 2 aqui pode clinicamente já ser
  estágio 3 sem que seja possível confirmar. NaN = dado insuficiente pra
  qualquer classificação (e a pessoa não é, de outra forma, estágio 4).

Uso (a partir da raiz do repositório):
    python src/derive_ckm_stage.py
"""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

REPO_ROOT = Path(__file__).parent.parent
INPUT_PATH = REPO_ROOT / "data" / "processed" / "pns_ckm_rce_2013.csv"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "pns_ckm_estagios_2013.csv"
LOG_PATH = OUTPUT_PATH.with_name(OUTPUT_PATH.stem + "_LINHAGEM.md")

# Colunas cujo NaN é ausência lógica (pergunta condicional), não dado perdido —
# decisão já documentada em docs/eda-pns-2013-achados.md (Grupo A). Recodificado
# só aqui, na camada derivada — o CSV de origem (Camada 1) permanece intocado.
COLUNAS_SKIP_PATTERN = ["Insuficiencia_Cardiaca", "Doenca_Coronariana", "Infarto_Miocardio"]

KDIGO_G_LIMIARES = [90, 60, 45, 30, 15]
KDIGO_G_LABELS = ["G1", "G2", "G3a", "G3b", "G4", "G5"]


def selecionar_categorico(condicoes: list, escolhas: list[str], index) -> pd.Series:
    """np.select com escolhas de texto + default=np.nan trava por promoção de
    dtype nesta versão do numpy (string vs. float não têm dtype comum). Contorna
    usando um marcador de texto como default e convertendo pra NaN depois,
    fora do np.select."""
    marcador = "__SEM_DADO__"
    resultado = np.select(condicoes, escolhas, default=marcador)
    return pd.Series(resultado, index=index).replace(marcador, np.nan)


def categoria_kdigo_g(egfr: pd.Series) -> pd.Series:
    condicoes = [egfr >= lim for lim in KDIGO_G_LIMIARES] + [egfr.notna()]
    return selecionar_categorico(condicoes, KDIGO_G_LABELS, egfr.index)


def sim_nao(valor_bruto: pd.Series, condicao: pd.Series) -> pd.Series:
    """'Sim'/'Nao' a partir de uma condição booleana, preservando NaN onde o
    valor de origem é ausente (comparação com NaN em pandas dá False, não NaN —
    por isso o mascaramento explícito é necessário)."""
    return pd.Series(np.where(condicao, "Sim", "Nao"), index=valor_bruto.index).where(valor_bruto.notna())


def main() -> None:
    log_lines: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        log_lines.append(msg)

    df = pd.read_csv(INPUT_PATH)
    log(f"Base de entrada: {INPUT_PATH.name} — {len(df)} linhas")

    for col in COLUNAS_SKIP_PATTERN:
        n_recodificado = df[col].isna().sum()
        df[col] = df[col].fillna("Nao")
        log(f"{col}: {n_recodificado} NaN recodificados para 'Nao' (ausência lógica, ver docs/eda-pns-2013-achados.md)")

    # --- Camada 2 ---
    df["Categoria_KDIGO_G"] = categoria_kdigo_g(df["eGFR_CKD_EPI_2021"])

    # --- Camada 3 ---
    df["Obesidade"] = sim_nao(df["IMC"], df["IMC"] >= 30)
    df["Obesidade_Central"] = sim_nao(df["RCE"], df["RCE"] >= 0.5)

    condicoes_glicemia = [
        df["Diabetes_Diagnosticado"] == "Sim",
        df["HbA1c_pct"] >= 6.5,
        df["HbA1c_pct"] >= 5.7,
        df["HbA1c_pct"].notna(),
    ]
    df["Classificacao_Glicemica"] = selecionar_categorico(
        condicoes_glicemia, ["Diabetes", "Diabetes", "Pre_Diabetes", "Normal"], df.index
    )

    condicoes_pa = [
        df["Hipertensao_Diagnosticada"] == "Sim",
        (df["PA_Sistolica_mmHg"] >= 130) | (df["PA_Diastolica_mmHg"] >= 80),
        df["PA_Sistolica_mmHg"].notna() & df["PA_Diastolica_mmHg"].notna(),
    ]
    df["Hipertensao_CKM"] = selecionar_categorico(condicoes_pa, ["Sim", "Sim", "Nao"], df.index)

    condicoes_lipide = [
        df["Colesterol_Alto_Diagnosticado"] == "Sim",
        df["Colesterol_Total_mgdL"] >= 200,
        df["Colesterol_Total_mgdL"].notna(),
    ]
    df["Dislipidemia"] = selecionar_categorico(condicoes_lipide, ["Sim", "Sim", "Nao"], df.index)

    # Síndrome metabólica (ATP III), com 3 dos 5 critérios oficiais — falta
    # triglicerídeos (ausente na PNS, ver especificação §3.C). Só calculado
    # quando os 4 critérios disponíveis estão presentes; não faz sentido
    # aproximar "3 de 4 disponíveis" quando parte deles já está ausente.
    limite_cintura = np.where(df["Sexo"] == "M", 102, 88)
    limite_hdl = np.where(df["Sexo"] == "M", 40, 50)
    criterio_cintura = df["Circunferencia_Cintura_cm"] >= limite_cintura
    criterio_hdl = df["HDL_mgdL"] < limite_hdl
    criterio_pa = (df["PA_Sistolica_mmHg"] >= 130) | (df["PA_Diastolica_mmHg"] >= 85)
    criterio_glicemia = df["Classificacao_Glicemica"].isin(["Diabetes", "Pre_Diabetes"])

    componentes_completos = (
        df["Sexo"].notna() & df["Circunferencia_Cintura_cm"].notna() & df["HDL_mgdL"].notna()
        & df["PA_Sistolica_mmHg"].notna() & df["PA_Diastolica_mmHg"].notna() & df["Classificacao_Glicemica"].notna()
    )
    n_criterios = criterio_cintura.astype(int) + criterio_hdl.astype(int) + criterio_pa.astype(int) + criterio_glicemia.astype(int)
    df["Sindrome_Metabolica_Parcial"] = pd.Series(
        np.where(n_criterios >= 3, "Sim", "Nao"), index=df.index
    ).where(componentes_completos)
    log(
        f"Sindrome_Metabolica_Parcial calculada só com os 4 critérios completos: "
        f"{componentes_completos.sum()} de {len(df)} pessoas ({componentes_completos.mean():.1%})"
    )

    # --- Camada 4 ---
    estagio4 = (
        (df["Infarto_Miocardio"] == "Sim") | (df["AVC"] == "Sim")
        | (df["Insuficiencia_Cardiaca"] == "Sim") | (df["Doenca_Coronariana"] == "Sim")
    )
    estagio2 = (
        (df["Classificacao_Glicemica"] == "Diabetes") | (df["Hipertensao_CKM"] == "Sim")
        | (df["Sindrome_Metabolica_Parcial"] == "Sim")
        | (df["Categoria_KDIGO_G"].isin(["G3a", "G3b", "G4", "G5"]))
    )
    estagio1 = (
        (df["Obesidade"] == "Sim") | (df["Obesidade_Central"] == "Sim")
        | (df["Classificacao_Glicemica"] == "Pre_Diabetes")
    )
    sem_info_suficiente = (
        df["Obesidade"].isna() & df["Obesidade_Central"].isna() & df["Classificacao_Glicemica"].isna()
        & df["Hipertensao_CKM"].isna() & df["Categoria_KDIGO_G"].isna() & df["Sindrome_Metabolica_Parcial"].isna()
        & ~estagio4
    )
    df["CKM_Stage"] = np.select(
        [estagio4, sem_info_suficiente, estagio2, estagio1], [4, np.nan, 2, 1], default=0
    )

    log("\nDistribuição de CKM_Stage (estágio 3 não existe nesta base — ver docstring do script):")
    for estagio, n in df["CKM_Stage"].value_counts(dropna=False).sort_index().items():
        log(f"  {estagio}: {n} ({n/len(df):.1%})")

    log("\nDistribuição dos classificadores da Camada 3:")
    for col in ["Obesidade", "Obesidade_Central", "Classificacao_Glicemica", "Hipertensao_CKM", "Dislipidemia", "Sindrome_Metabolica_Parcial", "Categoria_KDIGO_G"]:
        log(f"  {col}: {dict(df[col].value_counts(dropna=False))}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    log(f"\n{len(df)} linhas salvas em {OUTPUT_PATH}")

    LOG_PATH.write_text(
        f"# Linhagem — {OUTPUT_PATH.name}\n\n"
        f"Gerado em {datetime.now().isoformat(timespec='seconds')} a partir de "
        f"`{INPUT_PATH.name}`, aplicando `.spec/especificacao-estagios-ckm.md`.\n\n"
        "```\n" + "\n".join(log_lines) + "\n```\n",
        encoding="utf-8",
    )
    print(f"Log de linhagem salvo em {LOG_PATH}")


if __name__ == "__main__":
    main()
