"""
Valida a fidelidade de CKM_Stage e CKM_Stage_Com_PREVENT em
data/processed/pns_ckm_prevent_2013.csv — não confia que src/derive_ckm_stage.py
e src/calcular_prevent.R fizeram a coisa certa, prova isso checando invariantes
lógicas que TÊM que ser verdade se a hierarquia estiver implementada corretamente.

Duas partes:
  A. Recalcula os classificadores da Camada 3 (Obesidade, Hipertensao_CKM,
     Classificacao_Glicemica, Sindrome_Metabolica_Parcial, Categoria_KDIGO_G)
     de forma independente, a partir das colunas brutas/derivadas da Camada 1-2
     — não reaproveita a lógica de derive_ckm_stage.py, reimplementa do zero,
     pelo mesmo motivo que tests/validar_extracao_pns.py recalcula IMC/RCE/eGFR
     de forma independente em vez de confiar no valor já calculado.
  B. Verifica que CKM_Stage e CKM_Stage_Com_PREVENT são consequência lógica
     necessária e suficiente dos classificadores da Camada 3 (bidirecional:
     todo mundo no estágio X cumpre o critério do estágio X, e ninguém que
     cumpre o critério fica de fora dele).

Uso (a partir da raiz do repositório):
    python tests/validar_ckm_stage.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
CSV_PATH = REPO_ROOT / "data" / "processed" / "pns_ckm_prevent_2013.csv"


def comparar_categorico(a: pd.Series, b: pd.Series) -> int:
    ambos_nan = a.isna() & b.isna()
    iguais = a == b
    return int((~(ambos_nan | iguais)).sum())


def recalcular_camada3(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Reimplementação independente dos classificadores — mesmos limiares
    clínicos documentados em .spec/especificacao-estagios-ckm.md, mas
    calculados aqui do zero, não importados de derive_ckm_stage.py."""

    def sn(cond: pd.Series, base_notna: pd.Series) -> pd.Series:
        return pd.Series(np.where(cond, "Sim", "Nao"), index=df.index).where(base_notna)

    # IMC/RCE recalculados a partir de Peso/Altura/Cintura brutos, NAO lidos
    # da coluna IMC/RCE do CSV — pandas.to_csv() perde precisao de ponto
    # flutuante ao serializar, o que pode empurrar um valor como 29,999999993
    # (que é < 30, resultado correto do pipeline) para exatamente "30.0" no
    # arquivo, mudando o resultado da comparação ">= 30" por um artefato de
    # arredondamento, não por diferença real de lógica.
    imc_fresco = df["Peso_kg"] / (df["Altura_cm"] / 100) ** 2
    rce_fresco = df["Circunferencia_Cintura_cm"] / df["Altura_cm"]
    obesidade = sn(imc_fresco >= 30, imc_fresco.notna())
    obesidade_central = sn(rce_fresco >= 0.5, rce_fresco.notna())

    glicemia = pd.Series(np.nan, index=df.index, dtype=object)
    glicemia[df["HbA1c_pct"].notna()] = "Normal"
    glicemia[df["HbA1c_pct"] >= 5.7] = "Pre_Diabetes"
    glicemia[df["HbA1c_pct"] >= 6.5] = "Diabetes"
    glicemia[df["Diabetes_Diagnosticado"] == "Sim"] = "Diabetes"

    pa_completa = df["PA_Sistolica_mmHg"].notna() & df["PA_Diastolica_mmHg"].notna()
    hipertensao = pd.Series(np.nan, index=df.index, dtype=object)
    hipertensao[pa_completa] = "Nao"
    hipertensao[(df["PA_Sistolica_mmHg"] >= 130) | (df["PA_Diastolica_mmHg"] >= 80)] = "Sim"
    hipertensao[df["Hipertensao_Diagnosticada"] == "Sim"] = "Sim"

    limite_cintura = np.where(df["Sexo"] == "M", 102, 88)
    limite_hdl = np.where(df["Sexo"] == "M", 40, 50)
    criterio_cintura = df["Circunferencia_Cintura_cm"] >= limite_cintura
    criterio_hdl = df["HDL_mgdL"] < limite_hdl
    criterio_pa = (df["PA_Sistolica_mmHg"] >= 130) | (df["PA_Diastolica_mmHg"] >= 85)
    criterio_glicemia = glicemia.isin(["Diabetes", "Pre_Diabetes"])
    completos = (
        df["Sexo"].notna() & df["Circunferencia_Cintura_cm"].notna() & df["HDL_mgdL"].notna()
        & pa_completa & glicemia.notna()
    )
    n_criterios = criterio_cintura.astype(int) + criterio_hdl.astype(int) + criterio_pa.astype(int) + criterio_glicemia.astype(int)
    metabolica = pd.Series(np.where(n_criterios >= 3, "Sim", "Nao"), index=df.index).where(completos)

    egfr = df["eGFR_CKD_EPI_2021"]
    kdigo_g = pd.Series(np.nan, index=df.index, dtype=object)
    for limite, rotulo in [(0, "G5"), (15, "G4"), (30, "G3b"), (45, "G3a"), (60, "G2"), (90, "G1")]:
        kdigo_g[egfr >= limite] = rotulo

    return {
        "Obesidade": obesidade, "Obesidade_Central": obesidade_central,
        "Classificacao_Glicemica": glicemia, "Hipertensao_CKM": hipertensao,
        "Sindrome_Metabolica_Parcial": metabolica, "Categoria_KDIGO_G": kdigo_g,
    }


def validar() -> list[str]:
    print(f"Lendo {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"{len(df)} linhas\n")

    erros: list[str] = []

    print("--- Parte A: recalculando Camada 3 de forma independente ---")
    recalculado = recalcular_camada3(df)
    for coluna, esperado in recalculado.items():
        n_div = comparar_categorico(esperado, df[coluna])
        status = "OK" if n_div == 0 else f"FALHOU ({n_div} divergência(s))"
        print(f"  {coluna}: {status}")
        if n_div:
            erros.append(f"Camada 3 — {coluna}: {n_div} linha(s) divergente(s) da reimplementação independente")

    print("\n--- Parte B: invariantes da hierarquia CKM_Stage ---")
    clinica = (
        (df["Infarto_Miocardio"] == "Sim") | (df["AVC"] == "Sim")
        | (df["Insuficiencia_Cardiaca"] == "Sim") | (df["Doenca_Coronariana"] == "Sim")
    )
    risco2 = (
        (recalculado["Classificacao_Glicemica"] == "Diabetes") | (recalculado["Hipertensao_CKM"] == "Sim")
        | (recalculado["Sindrome_Metabolica_Parcial"] == "Sim")
        | (recalculado["Categoria_KDIGO_G"].isin(["G3a", "G3b", "G4", "G5"]))
    )
    adiposidade1 = (
        (recalculado["Obesidade"] == "Sim") | (recalculado["Obesidade_Central"] == "Sim")
        | (recalculado["Classificacao_Glicemica"] == "Pre_Diabetes")
    )
    sem_info = (
        recalculado["Obesidade"].isna() & recalculado["Obesidade_Central"].isna()
        & recalculado["Classificacao_Glicemica"].isna() & recalculado["Hipertensao_CKM"].isna()
        & recalculado["Categoria_KDIGO_G"].isna() & recalculado["Sindrome_Metabolica_Parcial"].isna()
        & ~clinica
    )
    stage_esperado = pd.Series(
        np.select([clinica, sem_info, risco2, adiposidade1], ["4", "nan", "2", "1"], default="0"),
        index=df.index,
    ).replace("nan", np.nan).astype(float)

    n_div = comparar_categorico(stage_esperado, df["CKM_Stage"].astype(float))
    print(f"  CKM_Stage bate com a hierarquia (clínica > risco2 > adiposidade1 > 0): {'OK' if n_div == 0 else f'FALHOU ({n_div})'}")
    if n_div:
        erros.append(f"CKM_Stage: {n_div} linha(s) não batem com a hierarquia esperada a partir dos classificadores")

    print("\n--- Parte C: invariantes de CKM_Stage_Com_PREVENT ---")
    stage4_mantido = df.loc[df["CKM_Stage"] == 4, "CKM_Stage_Com_PREVENT"]
    n_div = int((stage4_mantido != 4).sum())
    print(f"  Todo Estágio 4 original continua Estágio 4 com PREVENT: {'OK' if n_div == 0 else f'FALHOU ({n_div})'}")
    if n_div:
        erros.append(f"CKM_Stage_Com_PREVENT: {n_div} pessoa(s) em Estágio 4 original não ficaram em 4")

    deveria_subir = (df["Risco_PREVENT_10anos_pct"] >= 20) & (df["CKM_Stage"] != 4)
    n_div = int((df.loc[deveria_subir, "CKM_Stage_Com_PREVENT"] != 3).sum())
    print(f"  Todo mundo com PREVENT>=20% (e não Estágio 4) virou Estágio 3: {'OK' if n_div == 0 else f'FALHOU ({n_div})'}")
    if n_div:
        erros.append(f"CKM_Stage_Com_PREVENT: {n_div} pessoa(s) com PREVENT>=20% não foram promovidas a Estágio 3")

    nao_deveria_mudar = ~deveria_subir & (df["CKM_Stage"] != 4)
    divergentes = comparar_categorico(
        df.loc[nao_deveria_mudar, "CKM_Stage"].astype(float),
        df.loc[nao_deveria_mudar, "CKM_Stage_Com_PREVENT"].astype(float),
    )
    print(f"  Ninguém mudou de estágio sem critério pra isso: {'OK' if divergentes == 0 else f'FALHOU ({divergentes})'}")
    if divergentes:
        erros.append(f"CKM_Stage_Com_PREVENT: {divergentes} pessoa(s) mudaram de estágio sem cumprir o critério de PREVENT>=20%")

    return erros


if __name__ == "__main__":
    problemas = validar()
    print()
    if problemas:
        print(f"[FALHOU] {len(problemas)} problema(s) encontrado(s):")
        for p in problemas:
            print(f"  - {p}")
        sys.exit(1)
    else:
        print("[OK] CKM_Stage e CKM_Stage_Com_PREVENT são consequência lógica fiel dos classificadores em todas as linhas.")
