# Linhagem e checagem de qualidade — pns_ckm_rce_2013.csv

Gerado em 2026-08-31T11:48:28 a partir do arquivo de exames laboratoriais da PNS 2013 (Fiocruz/ICICT), `https://www.pns.icict.fiocruz.br/wp-content/uploads/2023/05/PNS2013_Exames.zip`.

```
Arquivo de exames PNS 2013 (Fiocruz/ICICT): 8952 pessoas, 23 colunas lidas
Este arquivo já vem com o questionário principal e os exames laboratoriais cruzados por pessoa pela Fiocruz — não há junção de múltiplos arquivos a fazer aqui (diferente do pipeline NHANES).
eGFR (CKD-EPI 2021, sem coeficiente de raça) calculado a partir da creatinina para 8952 adultos (0 menores de 18 anos ficaram com NaN de propósito). A PNS também disponibiliza um eGFR pré-calculado (fórmula CKD-EPI 2009, com coeficiente de raça) — não usado aqui para manter consistência metodológica com o pipeline NHANES, que usa a fórmula 2021.

Nota de proveniência: este arquivo não traz um identificador único de pessoa (a Fiocruz remove as chaves de ligação do PNS principal na versão de exames). 'ID_Participante' é um índice sequencial sintético criado aqui, não um código oficial do IBGE.

Checagem de plausibilidade clínica (fora da faixa é reportado, NÃO removido automaticamente):
  RCE: 0 valor(es) fora de [0.25, 1.3]
  IMC: 0 valor(es) fora de [10, 80]
  eGFR_CKD_EPI_2021: 0 valor(es) fora de [0, 200]
  PA_Sistolica_mmHg: 0 valor(es) fora de [60, 260]
  PA_Diastolica_mmHg: 0 valor(es) fora de [30, 160]

Valores ausentes por coluna:
  ID_Participante: 0 (0.0%)
  Idade: 0 (0.0%)
  Sexo: 0 (0.0%)
  Raca_Etnia: 2 (0.0%)
  Regiao: 6 (0.1%)
  Peso_kg: 97 (1.1%)
  Altura_cm: 97 (1.1%)
  Circunferencia_Cintura_cm: 97 (1.1%)
  IMC: 97 (1.1%)
  RCE: 97 (1.1%)
  PA_Sistolica_mmHg: 97 (1.1%)
  PA_Diastolica_mmHg: 97 (1.1%)
  Colesterol_Total_mgdL: 418 (4.7%)
  HDL_mgdL: 432 (4.8%)
  LDL_mgdL: 418 (4.7%)
  HbA1c_pct: 411 (4.6%)
  Creatinina_Serica_mgdL: 417 (4.7%)
  eGFR_CKD_EPI_2021: 417 (4.7%)
  Diabetes_Diagnosticado: 1125 (12.6%)
  Hipertensao_Diagnosticada: 426 (4.8%)
  Colesterol_Alto_Diagnosticado: 1390 (15.5%)
  Insuficiencia_Cardiaca: 8548 (95.5%)
  Doenca_Coronariana: 8548 (95.5%)
  Infarto_Miocardio: 8548 (95.5%)
  AVC: 8 (0.1%)
  Sintoma_Dor_Desconforto_Peito: 183 (2.0%)
  Peso_Amostral: 0 (0.0%)

Para Insuficiencia_Cardiaca/Doenca_Coronariana/Infarto_Miocardio (Q06303/Q06302/Q06301), a alta taxa de ausência não é dado perdido: só é perguntado a quem respondeu 'Sim' à pergunta guarda-chuva 'algum médico já lhe deu diagnóstico de doença do coração' (Q063).

8952 linhas salvas em C:\Users\caroo\OneDrive\Desktop\FIAP\projetos\cardioIA\data\processed\pns_ckm_rce_2013.csv
```
