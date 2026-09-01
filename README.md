# CardioIA — Diagnóstico e Alerta Precoce da Síndrome Cardiorrenal Metabólica (Fase 1)

Este repositório contém a entrega da **Fase 1: Batimentos de Dados** do projeto **CardioIA**, desenvolvido no curso de Inteligência Artificial da **FIAP**. O objetivo desta etapa é estruturar, catalogar e aplicar princípios de Governança de Dados em ativos numéricos, textuais e visuais voltados ao ecossistema da cardiologia moderna.

---

## Visão Geral do Projeto & Foco Clínico

O **CardioIA** é um sistema de suporte à decisão clínica (*Clinical Decision Support System - CDSS*) focado no contexto ambulatorial. Supervisionado e validado clinicamente pela Dra. Fernanda Fassina (Cardiologista e Clínica Geral - CRM-SP 169944), o projeto atua no mapeamento e **Alerta Precoce da Síndrome Cardiorrenal Metabólica (CKM)** e **Insuficiência Cardíaca Compensada / Pós-Infarto**.

O projeto resolve a dificuldade enfrentada por médicos em cruzar, durante consultas rápidas, exames de diferentes especialidades (metabólica, renal e eletrofisiológica). A IA atua unificando esses pontos para identificar o risco do paciente antes que o quadro evolua para desfechos graves.

---

## Descrição dos Datasets Integrados

> **Por que 3 fontes separadas, e não uma única base?** Investigamos 19 bases públicas candidatas (MIMIC-IV, UK Biobank, All of Us, MESA/BioLINCC, PTB-XL, CODE-15%, EchoNet, ACDC, entre outras) em busca de uma única fonte gratuita, aberta, redistribuível e com números clínicos completos + textos + ≥100 imagens cardíacas. Nenhuma cumpre tudo: as bases clinicamente mais completas (MIMIC-IV, UK Biobank, All of Us) exigem credenciamento e proíbem redistribuição por contrato; as bases livres para redistribuir (PNS, PTB-XL, Kaggle/Mendeley ECG) cobrem só uma fatia do conteúdo clínico. A comparação completa, com fontes citadas, está em [`.spec/decisao-fontes-de-dados.md`](.spec/decisao-fontes-de-dados.md). **Nota de proveniência:** as 3 partes abaixo vêm de indivíduos diferentes — a combinação é pedagógica (uma competência de governança por tipo de dado), não uma coorte real unificada.

### Parte 1 — Dados Numéricos (IoT & Laboratorial)
* **Objetivo Clínico:** Treinar classificadores para estimar, numa única base, risco metabólico, disfunção renal e risco cardiovascular (Insuficiência Cardíaca e Infarto) — endereçando o problema central do projeto: esses três eixos hoje são avaliados por especialistas diferentes (nefrologista, endocrinologista, cardiologista), e o cruzamento das informações costuma acontecer tarde demais.
* **Base Escolhida:** [PNS](https://www.pns.icict.fiocruz.br/) (Pesquisa Nacional de Saúde) 2013 + módulo de exames laboratoriais (coleta domiciliar 2014-2015) — pesquisa pública oficial do IBGE em parceria com o Ministério da Saúde, dados publicados pela Fundação Oswaldo Cruz (Fiocruz/ICICT). Dados **reais**, individuais, população **brasileira**. Peso, altura, cintura e pressão arterial são **medidos** por técnico treinado (não autorreferidos); os desfechos clínicos são autorreferidos pelo participante — ver limitações no SDD.
* **Por que PNS e não NHANES:** a base numérica deste projeto usava originalmente o NHANES (CDC/EUA). Trocamos para a PNS para eliminar o viés de população documentado na seção de Governança abaixo — o NHANES representa os EUA, não o Brasil/SUS, que é o alvo real do CardioIA. Avaliamos as 3 edições da PNS: a mais recente publicada (2019) não tem exame de sangue/urina; a próxima com exames (3ª edição, em coleta desde jul/2026) ainda não tem microdado disponível; a PNS 2013 é a única com biomarcadores reais publicados hoje. Justificativa completa em [`.spec/decisao-fontes-de-dados.md`](.spec/decisao-fontes-de-dados.md).
* **Origem e reprodutibilidade:** o dataset não é um arquivo estático — é reconstruído por um pipeline próprio ([`src/build_pns_ckm_dataset.py`](src/build_pns_ckm_dataset.py)) que baixa o arquivo oficial da Fiocruz (questionário + exames já cruzados por pessoa) e deriva os indicadores clínicos (IMC, RCE, eGFR CKD-EPI 2021). Garantias de fidelidade do tratamento, dicionário de dados completo e as limitações conhecidas estão documentadas em [`.spec/SDD-pipeline-pns-ckm.md`](.spec/SDD-pipeline-pns-ckm.md). Uma exploração inicial em R está em [`notebooks/exploracao_pns.R`](notebooks/exploracao_pns.R).
* **Variáveis Relevantes:**
  * `Idade` / `Sexo` / `Raca_Etnia` / `Regiao`: fatores de risco demográficos primários.
  * `RCE` (Relação Cintura-Estatura): indicador de obesidade central — evidência recente mostra que prediz Insuficiência Cardíaca melhor que o IMC, por capturar gordura visceral.
  * `Creatinina_Serica_mgdL` / `eGFR_CKD_EPI_2021`: pilar **renal** da Síndrome CKM (sem albuminúria — a PNS não coleta esse marcador, ver limitações no SDD).
  * `HbA1c_pct` / `Colesterol_Total_mgdL` / `HDL_mgdL` / `LDL_mgdL`: pilar **metabólico** (sem glicemia direta — só HbA1c, ver SDD).
  * `PA_Sistolica_mmHg` / `PA_Diastolica_mmHg`: sinais vitais cardiovasculares, medidos por aparelho.
  * `Sintoma_Dor_Desconforto_Peito`: item do Rose Angina Questionnaire (protocolo validado).
  * `Insuficiencia_Cardiaca` / `Infarto_Miocardio` / `Doenca_Coronariana` / `AVC` / `Diabetes_Diagnosticado` / `Hipertensao_Diagnosticada` / `Colesterol_Alto_Diagnosticado`: desfechos/comorbidades autorreferidos, usados como rótulo (*target*) dos classificadores.

  Essas variáveis foram escolhidas porque, juntas, permitem calcular para o mesmo paciente os três eixos da Síndrome CKM — o cruzamento tardio entre eles é exatamente o que a Dra. Fernanda Fassina identificou como a principal causa de diagnóstico tardio de IC e infarto na prática clínica.

| Fonte do Dataset | Volume de Dados | Formato | Aplicação em IA |
| :--- | :--- | :--- | :--- |
| **PNS 2013 + Exames Laboratoriais (IBGE/Fiocruz)** | 8.952 registros, 27 variáveis | `.csv` | Classificação de risco CKM / Previsão de Insuficiência Cardíaca e Infarto |

---

### Parte 2 — Dados Textuais (NLP & Suporte à Decisão)
> **Status: concluído.** Textos reais extraídos de fontes abertas, com o PDF original de cada um destacado (highlight) exatamente nos trechos usados — pasta `assets/documentos_cientificos/`.

* **Objetivo Clínico:** Alimentar modelos de Processamento de Linguagem Natural (NLP) para extração de entidades clínicas e consulta a diretrizes de tratamento em tempo real.
* **Documentos** (`assets/documentos_cientificos/<nome>/`, cada pasta com `recorte.txt` + `original.pdf` + `destacado.pdf`):
  1. [`diretriz_insuficiencia_cardiaca/`](assets/documentos_cientificos/diretriz_insuficiencia_cardiaca/): recorte da *Diretriz Brasileira de Insuficiência Cardíaca Crônica e Aguda* (SBC/DEIC, Arq Bras Cardiol 2018;111(3):436-539, [SciELO](https://www.scielo.br/j/abc/a/XkVKFb4838qXrXSYbmCYM3K/), DOI [10.5935/abc.20180190](https://doi.org/10.5935/abc.20180190)) — conceitos e estágios, diagnóstico e tratamento farmacológico/não farmacológico da IC crônica e aguda. Licença **CC BY 4.0** (declarada na própria página do artigo).
  2. [`consenso_sindrome_cardiorrenal/`](assets/documentos_cientificos/consenso_sindrome_cardiorrenal/): revisão sistemática *"Síndrome Cardiorrenal Aguda: Qual Critério Diagnóstico Utilizar e sua Importância para o Prognóstico?"* (Leite et al., Arq Bras Cardiol, 2020, DOI [10.36660/abc.20190207](https://doi.org/10.36660/abc.20190207)) — classificação, critérios diagnósticos, biomarcadores e prognóstico da síndrome cardiorrenal. Licença **CC BY-NC** (uso não comercial, com atribuição — compatível com o uso educacional deste projeto).
  3. [`ckm_current_urgent_concept/`](assets/documentos_cientificos/ckm_current_urgent_concept/): *"Cardiovascular-Kidney-Metabolic Syndrome: A Current and Urgent Concept"* (Jornal Brasileiro de Nefrologia/SciELO, 2025, DOI [10.1590/2175-8239-JBN-2024-0277en](https://doi.org/10.1590/2175-8239-JBN-2024-0277en)) — artigo brasileiro sobre a diretriz AHA/ACC/ADA/ASN de CKM (a mesma base clínica usada na Parte 1 pra derivar `CKM_Stage`, ver `.spec/especificacao-estagios-ckm.md`). Licença **CC BY 4.0**. Publicado em inglês, com resumo também em português (incluído no arquivo).
* **PDF destacado:** gerado por [`src/destacar_documentos_cientificos.py`](src/destacar_documentos_cientificos.py) — baixa o `original.pdf` de cada artigo e marca em amarelo os trechos que foram efetivamente usados no `recorte.txt` (~85% de cobertura de destaque; o `.txt` continua sendo a fonte de verdade do que foi usado, o PDF é só uma conferência visual).
* **Aplicações de NLP:** Sumarização automática de condutas, extração de sintomas e sistemas RAG (*Retrieval-Augmented Generation*) para auxílio ao médico.
* **Nota:** os 3 arquivos são recortes selecionados dos documentos originais (não o texto integral), com cabeçalho de citação completo (fonte, DOI, licença, data de extração) no topo de cada `.txt`.

---

### Parte 3 — Dados Visuais (Visão Computacional)
> **Status: concluído.** 120 imagens reais de ECG baixadas e organizadas por classe em `assets/imagens_ecg/`.

* **Objetivo Clínico:** Identificação de padrões morfológicos no traçado elétrico do coração para validação cruzada do risco numérico.
* **Base Utilizada:** Mendeley Data — *"ECG Images dataset of Cardiac Patients"* (Khan, Hussain & Malik, Ch. Pervaiz Elahi Institute of Cardiology, Multan/Paquistão), versão 2, DOI [10.17632/gwbz3fsgp8.2](http://dx.doi.org/10.17632/gwbz3fsgp8.2). Traçados de ECG de 12 derivações, dispositivo EDAN SERIES-3.
* **Volume:** dataset de origem tem 928 imagens em 4 classes (615 MB); este repositório contém uma **amostra balanceada de 120 imagens (30 por classe)**, acima do mínimo de 100 exigido. Detalhes de seleção e reprodutibilidade em [`assets/imagens_ecg/LINHAGEM.md`](assets/imagens_ecg/LINHAGEM.md).
* **Classes:** `Normal` (284 na fonte / 30 baixadas), `Infarto_Miocardio` — MI (239/30), `Historico_Infarto_Miocardio` — PMI, infarto prévio (172/30), `Batimento_Anormal` — HB, arritmia (233/30).
* **Aplicações em VC:** Redes Neurais Convolucionais (CNNs) para detecção de anomalias visuais e identificação de bordas/picos nos exames gráficos.
* **Licença:** **CC BY 4.0**, confirmado no campo `data_licence` da API pública do Mendeley Data — redistribuição permitida com atribuição. As imagens não trazem PII do paciente (verificado por inspeção visual: campos de idade/peso/altura do laudo aparecem em branco no template, só há um ID numérico interno).

---

## Links Públicos para Acesso aos Dados

Em conformidade com os requisitos de entrega, os conjuntos completos de dados devem estar hospedados na nuvem, com link acessível para qualquer pessoa (necessário para a correção da FIAP). Os 3 conjuntos já estão gerados e organizados localmente (`data/processed/`, `assets/`) — falta apenas o upload para Drive/OneDrive e a cola do link abaixo:

* **Dados Numéricos** (`data/processed/pns_ckm_rce_2013.csv`): **[INSIRA_AQUI_O_LINK_PÚBLICO_DO_SEU_GOOGLE_DRIVE_OU_ONEDRIVE]**
* **Dados Textuais** (pasta `assets/*.txt`): **[INSIRA_AQUI_O_LINK_PÚBLICO_DO_SEU_GOOGLE_DRIVE_OU_ONEDRIVE]**
* **Dados Visuais** (pasta `assets/imagens_ecg/`): **[INSIRA_AQUI_O_LINK_PÚBLICO_DO_SEU_GOOGLE_DRIVE_OU_ONEDRIVE]**

---

## Governança de Dados, Viés e LGPD

O desenvolvimento da base do CardioIA segue os princípios formais de Governança de IA (NIST AI RMF e DAMA-DMBOK2):

* **Privacidade e LGPD:** Os dados numéricos (PNS/IBGE-Fiocruz) são microdados desidentificados do governo brasileiro, sob a Lei de Acesso à Informação e a política de Dados Abertos do IBGE, sem qualquer dado pessoal identificável (PII) e sem chave que permita religar à pesquisa original em nível de pessoa. Os dados textuais (SciELO/Arq Bras Cardiol) são literatura científica publicada, sem dado de paciente. As imagens de ECG (Mendeley) foram verificadas por inspeção visual e não trazem PII — ver [`assets/imagens_ecg/LINHAGEM.md`](assets/imagens_ecg/LINHAGEM.md).
* **Análise de Viés Algorítmico:** A base numérica agora é **brasileira** (PNS/IBGE) — decisão tomada justamente para eliminar o viés de população que existia quando o projeto usava o NHANES (EUA). Viés residual que permanece: os dados são de 2014-2015 (mais antigos que um ciclo NHANES recente), a amostra do módulo de exames é menor (8.952 pessoas) que a pesquisa PNS completa, e a PNS usa amostragem complexa com peso amostral próprio (`peso_lab`/`Peso_Amostral`) não aplicado neste dataset bruto — estatísticas descritivas simples não são diretamente representativas da população brasileira sem esse ajuste. Detalhes em [`.spec/SDD-pipeline-pns-ckm.md`](.spec/SDD-pipeline-pns-ckm.md).
* **Cadeia Evolutiva D-I-C-I:**
  * **Dado:** Métricas brutas de creatinina, pressão arterial e pixels das imagens de ECG.
  * **Informação:** Cálculo da probabilidade de risco (ex.: "Paciente em Risco CKM Estágio 2 com 84% de probabilidade").
  * **Conhecimento:** Cruzamento do diagnóstico probabilístico com o arquivo `.txt` de diretrizes da SBC.
  * **Inteligência:** Recomendação automática de protocolo preventivo e alerta ao cardiologista.

---

## Estrutura do Repositório

```text
├── data/
│   ├── raw/                                    # cache imutável do zip de exames da PNS (não versionado)
│   └── processed/                              # datasets finais, prontos para análise
│       ├── pns_ckm_rce_2013.csv                # Parte 1 — dataset numérico (Camada 1)
│       ├── pns_ckm_rce_2013_LINHAGEM.md        # log de linhagem/qualidade (gerado a cada execução)
│       ├── pns_ckm_estagios_2013.csv           # Camada 1 + classificadores + CKM_Stage
│       ├── pns_ckm_estagios_2013_LINHAGEM.md   # log de linhagem da derivação de estágios
│       ├── pns_ckm_prevent_2013.csv            # + risco PREVENT e CKM_Stage_Com_PREVENT (Estágio 3 real)
│       └── pns_ckm_prevent_2013_LINHAGEM.md    # log de linhagem do cálculo de PREVENT
├── src/
│   ├── build_pns_ckm_dataset.py                # pipeline: baixa, seleciona e valida o dataset numérico
│   ├── derive_ckm_stage.py                     # deriva classificadores clínicos e CKM_Stage (Camadas 2-4)
│   ├── calcular_prevent.R                      # Estágio 3 via escore PREVENT (pacote CVrisk, só em R)
│   └── destacar_documentos_cientificos.py      # baixa e destaca (highlight) os PDFs originais da Parte 2
├── tests/
│   ├── validar_extracao_pns.py                 # compara bruto (Excel) x tratado (CSV) linha a linha
│   └── validar_ckm_stage.py                    # prova que CKM_Stage é consequência lógica fiel dos classificadores
├── notebooks/
│   └── exploracao_pns.R                        # análise exploratória inicial (R)
├── docs/
│   └── eda-pns-2013-achados.md                 # achados da EDA: valores ausentes, outliers, casos investigados
├── .spec/
│   ├── SDD-pipeline-pns-ckm.md                 # especificação técnica do pipeline (Parte 1)
│   ├── especificacao-estagios-ckm.md           # mapa indicador→variável PNS→estágio CKM
│   └── decisao-fontes-de-dados.md              # por que 3 fontes separadas (e por que PNS, não NHANES)
├── assets/
│   ├── documentos_cientificos/                 # Parte 2 — 3 artigos, 1 subpasta por documento
│   │   ├── diretriz_insuficiencia_cardiaca/{recorte.txt,original.pdf,destacado.pdf}
│   │   ├── consenso_sindrome_cardiorrenal/{recorte.txt,original.pdf,destacado.pdf}
│   │   └── ckm_current_urgent_concept/{recorte.txt,original.pdf,destacado.pdf}
│   └── imagens_ecg/                            # Parte 3 — 120 imagens de ECG (CC BY 4.0)
│       ├── Normal/ · Infarto_Miocardio/ · Historico_Infarto_Miocardio/ · Batimento_Anormal/
│       ├── _manifest.json                      # arquivo, classe, tamanho e hash SHA-256 de cada imagem
│       └── LINHAGEM.md                         # fonte, licença, método de amostragem, reprodutibilidade
├── RELATORIO-FASE1.md                          # relatório técnico consolidando o projeto inteiro
├── requirements.txt
├── .gitignore
└── README.md