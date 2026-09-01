"""
Valida que data/processed/pns_ckm_rce_2013.csv (Camada 1) foi extraído
corretamente do arquivo bruto da PNS 2013 (Fiocruz/ICICT) — lê o Excel de
origem direto, recalcula o que o pipeline deveria ter gerado, e compara
linha a linha com o CSV final.

Reaproveita os mapeamentos e a fórmula de src/build_pns_ckm_dataset.py em vez
de duplicá-los aqui — se o pipeline mudar uma regra, este teste usa a regra
nova automaticamente, sem risco de os dois ficarem dessincronizados.

Cobre 3 tipos de transformação:
  1. Cópia direta (ex.: Z025 -> Creatinina_Serica_mgdL)
  2. Mapeamento categórico (ex.: Z001 -> Sexo, Q060 -> Colesterol_Alto_Diagnosticado)
  3. Derivados recalculados de forma independente (IMC, RCE, eGFR) — não reaproveita
     o valor já calculado pelo pipeline, recalcula do zero a partir do dado bruto

Uso (a partir da raiz do repositório):
    python tests/validar_extracao_pns.py            # valida as 8.952 linhas
    python tests/validar_extracao_pns.py 100         # valida só as 100 primeiras (mais rápido)
"""

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
import build_pns_ckm_dataset as pipeline  # noqa: E402 (import após ajuste de sys.path é intencional)

RAW_XLSX = REPO_ROOT / "data" / "raw" / "pns_2013_exames" / pipeline.RAW_XLSX_NAME
PROCESSED_CSV = REPO_ROOT / "data" / "processed" / "pns_ckm_rce_2013.csv"

# coluna bruta -> coluna tratada, pra cada tipo de checagem
COPIA_DIRETA = {
    "C008": "Idade", "z004": "Peso_kg", "z005": "Altura_cm",
    "W00303": "Circunferencia_Cintura_cm", "W00407": "PA_Sistolica_mmHg",
    "W00408": "PA_Diastolica_mmHg", "Z025": "Creatinina_Serica_mgdL",
    "Z031": "Colesterol_Total_mgdL", "Z032": "HDL_mgdL", "Z033": "LDL_mgdL",
    "Z034": "HbA1c_pct", "peso_lab": "Peso_Amostral", "regiao": "Regiao",
}
DIAGNOSTICO_COM_GRAVIDEZ = {"Q002": "Hipertensao_Diagnosticada", "Q030": "Diabetes_Diagnosticado"}
DIAGNOSTICO_SIMPLES = {
    "Q060": "Colesterol_Alto_Diagnosticado", "Q06301": "Infarto_Miocardio",
    "Q06302": "Doenca_Coronariana", "Q06303": "Insuficiencia_Cardiaca",
    "Q068": "AVC", "N005": "Sintoma_Dor_Desconforto_Peito",
}


def comparar_categorico(raw_col: pd.Series, tratado_col: pd.Series) -> int:
    """Divergências entre uma coluna bruta (já mapeada pro valor esperado) e a
    tratada, tratando NaN dos dois lados como 'igual' (ausência bate com ausência)."""
    ambos_nan = raw_col.isna() & tratado_col.isna()
    iguais = raw_col == tratado_col
    return int((~(ambos_nan | iguais)).sum())


def comparar_numerico(raw_col: pd.Series, tratado_col: pd.Series, tolerancia: float = 1e-6) -> int:
    ambos_nan = raw_col.isna() & tratado_col.isna()
    proximos = (raw_col - tratado_col).abs() <= tolerancia
    return int((~(ambos_nan | proximos)).sum())


def validar(n_amostras: int | None = None) -> list[str]:
    print(f"Lendo bruto:   {RAW_XLSX}")
    raw = pd.read_excel(RAW_XLSX, usecols=pipeline.RAW_COLUMNS_NEEDED, engine="openpyxl", nrows=n_amostras)
    print(f"Lendo tratado: {PROCESSED_CSV}")
    tratado = pd.read_csv(PROCESSED_CSV, nrows=n_amostras)
    print(f"{len(raw)} linhas de cada lado\n")

    erros: list[str] = []

    if len(raw) != len(tratado):
        erros.append(f"FALHA CRÍTICA: bruto tem {len(raw)} linhas, tratado tem {len(tratado)} — não é seguro comparar o resto linha a linha")
        return erros

    for col_bruta, col_tratada in COPIA_DIRETA.items():
        n_div = comparar_numerico(raw[col_bruta], tratado[col_tratada])
        if n_div:
            erros.append(f"{col_bruta} -> {col_tratada} (cópia direta): {n_div} linha(s) divergente(s)")

    sexo_esperado = raw["Z001"].map(pipeline.SEXO_MAP)
    n_div = comparar_categorico(sexo_esperado, tratado["Sexo"])
    if n_div:
        erros.append(f"Z001 -> Sexo: {n_div} linha(s) divergente(s)")

    raca_esperada = raw["Z003"].map(pipeline.RACA_MAP)
    n_div = comparar_categorico(raca_esperada, tratado["Raca_Etnia"])
    if n_div:
        erros.append(f"Z003 -> Raca_Etnia: {n_div} linha(s) divergente(s)")

    for col_bruta, col_tratada in DIAGNOSTICO_COM_GRAVIDEZ.items():
        esperado = raw[col_bruta].map(pipeline.DIAGNOSTICO_COM_GRAVIDEZ_MAP)
        n_div = comparar_categorico(esperado, tratado[col_tratada])
        if n_div:
            erros.append(f"{col_bruta} -> {col_tratada}: {n_div} linha(s) divergente(s)")

    for col_bruta, col_tratada in DIAGNOSTICO_SIMPLES.items():
        esperado = raw[col_bruta].map(pipeline.DIAGNOSTICO_SIMPLES_MAP)
        n_div = comparar_categorico(esperado, tratado[col_tratada])
        if n_div:
            erros.append(f"{col_bruta} -> {col_tratada}: {n_div} linha(s) divergente(s)")

    # Derivados: recalculados do zero a partir do bruto, não copiados do pipeline
    imc_esperado = raw["z004"] / (raw["z005"] / 100) ** 2
    n_div = comparar_numerico(imc_esperado, tratado["IMC"], tolerancia=0.01)
    if n_div:
        erros.append(f"IMC recalculado independentemente diverge em {n_div} linha(s) (tolerância 0,01)")

    rce_esperado = raw["W00303"] / raw["z005"]
    n_div = comparar_numerico(rce_esperado, tratado["RCE"], tolerancia=0.001)
    if n_div:
        erros.append(f"RCE recalculado independentemente diverge em {n_div} linha(s) (tolerância 0,001)")

    idade_valida = raw["C008"] >= 18
    egfr_esperado = pd.Series(
        [
            pipeline.ckd_epi_2021(scr, idade, sexo) if valido else float("nan")
            for scr, idade, sexo, valido in zip(raw["Z025"], raw["C008"], sexo_esperado, idade_valida)
        ],
        index=raw.index,
    )
    n_div = comparar_numerico(egfr_esperado, tratado["eGFR_CKD_EPI_2021"], tolerancia=0.01)
    if n_div:
        erros.append(f"eGFR recalculado independentemente diverge em {n_div} linha(s) (tolerância 0,01) — não testa se a fórmula está clinicamente certa, só se foi aplicada à pessoa certa")

    return erros


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    problemas = validar(n)
    print()
    if problemas:
        print(f"[FALHOU] {len(problemas)} problema(s) encontrado(s):")
        for p in problemas:
            print(f"  - {p}")
        sys.exit(1)
    else:
        print("[OK] Nenhuma divergência entre o dataset bruto e o tratado.")
