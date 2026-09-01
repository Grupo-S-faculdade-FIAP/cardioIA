"""
Baixa o arquivo de exames laboratoriais da PNS 2013 (Fiocruz/ICICT, coleta
2014-2015) e extrai as colunas necessarias para:
  - RCE (Relacao Cintura-Estatura / WHtR)
  - Eixo metabolico (IMC, HbA1c, colesterol total, HDL, LDL)
  - Eixo renal (creatinina, eGFR)
  - Eixo cardiovascular (pressao arterial medida, IC, infarto, angina, AVC)

Ao contrario do pipeline NHANES (12 arquivos para fundir), aqui a Fiocruz ja
disponibiliza um unico arquivo com o questionario principal e os exames
laboratoriais cruzados por pessoa — o pipeline so precisa selecionar,
renomear e derivar colunas, e checar plausibilidade.

Alem do CSV, gera um log de linhagem (*_LINHAGEM.md) com contagem de linhas,
taxa de dado ausente por coluna (distinguindo pergunta condicional de dado
perdido) e checagem de plausibilidade clinica dos valores derivados.

Uso (a partir da raiz do repositorio):
    pip install -r requirements.txt
    python src/build_pns_ckm_dataset.py
"""

import sys
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

EXAMES_URL = "https://www.pns.icict.fiocruz.br/wp-content/uploads/2023/05/PNS2013_Exames.zip"
REPO_ROOT = Path(__file__).parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "pns_2013_exames"
RAW_ZIP = RAW_DIR / "PNS2013_Exames.zip"
RAW_XLSX_NAME = "EXAMES-PNS-2013-FINAL_05052023.xlsx"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "pns_ckm_rce_2013.csv"
LOG_PATH = OUTPUT_PATH.with_name(OUTPUT_PATH.stem + "_LINHAGEM.md")

# nome da coluna no arquivo de origem -> coluna final. Ordem = ordem final do CSV.
COLUMN_MAP = {
    "C008": "Idade",
    "z004": "Peso_kg",
    "z005": "Altura_cm",
    "W00303": "Circunferencia_Cintura_cm",
    "W00407": "PA_Sistolica_mmHg",
    "W00408": "PA_Diastolica_mmHg",
    "Colesterol_Total_mgdL": "Colesterol_Total_mgdL",
    "HDL_mgdL": "HDL_mgdL",
    "LDL_mgdL": "LDL_mgdL",
    "HbA1c_pct": "HbA1c_pct",
    "Creatinina_Serica_mgdL": "Creatinina_Serica_mgdL",
    "peso_lab": "Peso_Amostral",
    "regiao": "Regiao",
}
# colunas brutas cujo nome ja e o rotulo do exame (renomeadas explicitamente abaixo)
RAW_LAB_COLUMNS = {
    "Z031": "Colesterol_Total_mgdL",
    "Z032": "HDL_mgdL",
    "Z033": "LDL_mgdL",
    "Z034": "HbA1c_pct",
    "Z025": "Creatinina_Serica_mgdL",
}

RAW_COLUMNS_NEEDED = [
    "Z001", "C008", "Z003", "z004", "z005",
    "W00303", "W00407", "W00408",
    "Z025", "Z031", "Z032", "Z033", "Z034",
    "Q002", "Q030", "Q060", "Q06301", "Q06302", "Q06303", "Q068", "N005",
    "peso_lab", "regiao",
]

SEXO_MAP = {1: "M", 2: "F"}

RACA_MAP = {1: "Branca", 2: "Preta", 3: "Amarela", 4: "Parda", 5: "Indigena"}  # 9=Ignorado -> NaN

# Q002 (hipertensao) e Q030 (diabetes) tem uma 3a categoria "so na gravidez"
# (codigo 2), que nao representa diagnostico cronico nem sua ausencia -> NaN.
# Chaves numericas (nao string): o pandas le essas colunas como float64 (1.0/2.0/3.0)
# por causa dos NaN presentes, mesmo o arquivo de origem guardando "1"/"2"/"3" como texto.
DIAGNOSTICO_COM_GRAVIDEZ_MAP = {1: "Sim", 3: "Nao"}
DIAGNOSTICO_SIMPLES_MAP = {1: "Sim", 2: "Nao"}

# faixas de plausibilidade clinica: valores fora daqui sao reportados, nao removidos
PLAUSIBILITY_RANGES = {
    "RCE": (0.25, 1.3),
    "IMC": (10, 80),
    "eGFR_CKD_EPI_2021": (0, 200),
    "PA_Sistolica_mmHg": (60, 260),
    "PA_Diastolica_mmHg": (30, 160),
}


def download_exames() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_ZIP.exists():
        import urllib.request
        print(f"Baixando exames laboratoriais da PNS 2013 de {EXAMES_URL}")
        urllib.request.urlretrieve(EXAMES_URL, RAW_ZIP)
    xlsx_path = RAW_DIR / RAW_XLSX_NAME
    if not xlsx_path.exists():
        with zipfile.ZipFile(RAW_ZIP) as zf:
            zf.extract(RAW_XLSX_NAME, RAW_DIR)
    return xlsx_path


def ckd_epi_2021(scr: float, age: float, sexo: str) -> float:
    """eGFR (mL/min/1.73m²) pela equação CKD-EPI 2021 sem coeficiente de raça
    (Inker et al., NEJM 2021) — mesma fórmula usada no pipeline NHANES, para
    manter as duas bases comparáveis mesmo a PNS trazendo um eGFR
    pré-calculado com a fórmula antiga (2009, com coeficiente de raça)."""
    if pd.isna(scr) or pd.isna(age) or sexo not in ("M", "F"):
        return np.nan
    kappa, alpha, fator_sexo = (0.7, -0.241, 1.012) if sexo == "F" else (0.9, -0.302, 1.0)
    return (
        142
        * min(scr / kappa, 1) ** alpha
        * max(scr / kappa, 1) ** -1.200
        * 0.9938 ** age
        * fator_sexo
    )


def main() -> None:
    log_lines: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        log_lines.append(msg)

    xlsx_path = download_exames()
    raw = pd.read_excel(xlsx_path, usecols=RAW_COLUMNS_NEEDED, engine="openpyxl")
    log(f"Arquivo de exames PNS 2013 (Fiocruz/ICICT): {len(raw)} pessoas, {len(raw.columns)} colunas lidas")
    log(
        "Este arquivo já vem com o questionário principal e os exames laboratoriais "
        "cruzados por pessoa pela Fiocruz — não há junção de múltiplos arquivos a "
        "fazer aqui (diferente do pipeline NHANES)."
    )

    df = raw.rename(columns=RAW_LAB_COLUMNS)

    df["Sexo"] = df["Z001"].map(SEXO_MAP)
    df["Raca_Etnia"] = df["Z003"].map(RACA_MAP)
    for col in ("Q002", "Q030"):
        df[col] = df[col].map(DIAGNOSTICO_COM_GRAVIDEZ_MAP)
    for col in ("Q060", "Q06301", "Q06302", "Q06303", "Q068", "N005"):
        df[col] = df[col].map(DIAGNOSTICO_SIMPLES_MAP)

    df["IMC"] = df["z004"] / (df["z005"] / 100) ** 2
    df["RCE"] = df["W00303"] / df["z005"]

    idade_valida = df["C008"] >= 18
    df["eGFR_CKD_EPI_2021"] = np.where(
        idade_valida,
        df.apply(lambda r: ckd_epi_2021(r["Creatinina_Serica_mgdL"], r["C008"], r["Sexo"]), axis=1),
        np.nan,
    )
    log(
        f"eGFR (CKD-EPI 2021, sem coeficiente de raça) calculado a partir da creatinina "
        f"para {idade_valida.sum()} adultos ({(~idade_valida).sum()} menores de 18 anos "
        f"ficaram com NaN de propósito). A PNS também disponibiliza um eGFR pré-calculado "
        f"(fórmula CKD-EPI 2009, com coeficiente de raça) — não usado aqui para manter "
        f"consistência metodológica com o pipeline NHANES, que usa a fórmula 2021."
    )

    final = df.rename(columns={
        "C008": "Idade",
        "z004": "Peso_kg",
        "z005": "Altura_cm",
        "W00303": "Circunferencia_Cintura_cm",
        "W00407": "PA_Sistolica_mmHg",
        "W00408": "PA_Diastolica_mmHg",
        "Q002": "Hipertensao_Diagnosticada",
        "Q030": "Diabetes_Diagnosticado",
        "Q060": "Colesterol_Alto_Diagnosticado",
        "Q06301": "Infarto_Miocardio",
        "Q06302": "Doenca_Coronariana",
        "Q06303": "Insuficiencia_Cardiaca",
        "Q068": "AVC",
        "N005": "Sintoma_Dor_Desconforto_Peito",
        "peso_lab": "Peso_Amostral",
        "regiao": "Regiao",
    })
    final.insert(0, "ID_Participante", range(1, len(final) + 1))
    final = final[[
        "ID_Participante", "Idade", "Sexo", "Raca_Etnia", "Regiao",
        "Peso_kg", "Altura_cm", "Circunferencia_Cintura_cm", "IMC", "RCE",
        "PA_Sistolica_mmHg", "PA_Diastolica_mmHg",
        "Colesterol_Total_mgdL", "HDL_mgdL", "LDL_mgdL", "HbA1c_pct",
        "Creatinina_Serica_mgdL", "eGFR_CKD_EPI_2021",
        "Diabetes_Diagnosticado", "Hipertensao_Diagnosticada", "Colesterol_Alto_Diagnosticado",
        "Insuficiencia_Cardiaca", "Doenca_Coronariana", "Infarto_Miocardio", "AVC",
        "Sintoma_Dor_Desconforto_Peito", "Peso_Amostral",
    ]]

    log(
        "\nNota de proveniência: este arquivo não traz um identificador único de pessoa "
        "(a Fiocruz remove as chaves de ligação do PNS principal na versão de exames). "
        "'ID_Participante' é um índice sequencial sintético criado aqui, não um código oficial do IBGE."
    )

    log("\nChecagem de plausibilidade clínica (fora da faixa é reportado, NÃO removido automaticamente):")
    for col, (lo, hi) in PLAUSIBILITY_RANGES.items():
        fora = final[col].notna() & ~final[col].between(lo, hi)
        log(f"  {col}: {fora.sum()} valor(es) fora de [{lo}, {hi}]")

    log("\nValores ausentes por coluna:")
    for col, n in final.isna().sum().items():
        log(f"  {col}: {n} ({n / len(final):.1%})")
    log(
        "\nPara Insuficiencia_Cardiaca/Doenca_Coronariana/Infarto_Miocardio (Q06303/Q06302/Q06301), "
        "a alta taxa de ausência não é dado perdido: só é perguntado a quem respondeu 'Sim' à "
        "pergunta guarda-chuva 'algum médico já lhe deu diagnóstico de doença do coração' (Q063)."
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    log(f"\n{len(final)} linhas salvas em {OUTPUT_PATH}")

    LOG_PATH.write_text(
        f"# Linhagem e checagem de qualidade — {OUTPUT_PATH.name}\n\n"
        f"Gerado em {datetime.now().isoformat(timespec='seconds')} a partir do arquivo de "
        f"exames laboratoriais da PNS 2013 (Fiocruz/ICICT), `{EXAMES_URL}`.\n\n"
        "```\n" + "\n".join(log_lines) + "\n```\n",
        encoding="utf-8",
    )
    print(f"Log de linhagem salvo em {LOG_PATH}")


if __name__ == "__main__":
    main()
