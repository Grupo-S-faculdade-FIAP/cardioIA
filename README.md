# CardioIA — Diagnóstico e Alerta Precoce da Síndrome Cardiorrenal Metabólica (Fase 1)

Este repositório contém a entrega da **Fase 1: Batimentos de Dados** do projeto **CardioIA**, desenvolvido no curso de Inteligência Artificial da **FIAP**. O objetivo desta etapa é estruturar, catalogar e aplicar princípios de Governança de Dados em ativos numéricos, textuais e visuais voltados ao ecossistema da cardiologia moderna.

---

## Visão Geral do Projeto & Foco Clínico

O **CardioIA** é um sistema de suporte à decisão clínica (*Clinical Decision Support System - CDSS*) focado no contexto ambulatorial. Supervisionado e validado clinicamente pela Dra. Fernanda Fassina (Cardiologista e Clínica Geral - CRM-SP 169944), o projeto atua no mapeamento e **Alerta Precoce da Síndrome Cardiorrenal Metabólica (CKM)** e **Insuficiência Cardíaca Compensada / Pós-Infarto**.

O projeto resolve a dificuldade enfrentada por médicos em cruzar, durante consultas rápidas, exames de diferentes especialidades (metabólica, renal e eletrofisiológica). A IA atua unificando esses pontos para identificar o risco do paciente antes que o quadro evolua para desfechos graves.

---

## Descrição dos Datasets Integrados

### Parte 1 — Dados Numéricos (Sinais Vitais & Laboratorial)
* **Objetivo Clínico:** Treinamento de classificadores para estimar a probabilidade de risco metabólico, disfunção renal e estresse miocárdico.
* **Bases Escolhidas:** *Heart Failure Clinical Records* (UCI / Kaggle) e *PTB-XL Database* (PhysioNet).
* **Variáveis Relevantes:**
  * `age` / `sex`: Mapeamento demográfico e fatores de risco primários.
  * `serum_creatinine`: Avaliação da função renal (pilar renal da CKM).
  * `serum_sodium`: Balanço eletrolítico e retenção de fluidos.
  * `ejection_fraction`: Porcentagem de sangue bombeado pelo coração a cada contração.
  * `high_blood_pressure` / `diabetes`: Comorbidades base do espectro metabólico.
  * **Contexto Biomarcador (NT-proBNP):** Mapeado na documentação para validar o grau de estresse hemodinâmico do miocárdio na Insuficiência Cardíaca.

| Fonte do Dataset | Volume de Dados | Formato | Aplicação em IA |
| :--- | :--- | :--- | :--- |
| **Kaggle / UCI (Heart Failure)** | 299 registros | `.csv` | Algoritmos de Classificação / Previsão de Risco |
| **PhysioNet (PTB-XL)** | 21.837 exames | `.csv` | Treinamento de Séries Temporais e Rótulos de ECG |

---

### Parte 2 — Dados Textuais (NLP & Suporte à Decisão)
* **Objetivo Clínico:** Alimentar modelos de Processamento de Linguagem Natural (NLP) para extração de entidades clínicas e consulta a diretrizes de tratamento em tempo real.
* **Arquivos Incluídos (Pasta `docs/assets`):**
  1. `diretriz_insuficiencia_cardiaca.txt`: Protocolo da Sociedade Brasileira de Cardiologia (SBC) para manejo e titulação de medicamentos em IC.
  2. `consenso_sindrome_cardiorrenal.txt`: Literatura oficial sobre rastreio, diagnóstico e estadiamento da Síndrome CKM.
* **Aplicações de NLP:** Sumarização automática de condutas, extração de sintomas e sistemas RAG (*Retrieval-Augmented Generation*) para auxílio ao médico.

---

### Parte 3 — Dados Visuais (Visão Computacional)
* **Objetivo Clínico:** Identificação de padrões morfológicos no traçado elétrico do coração para validação cruzada do risco numérico.
* **Base Escolhida:** *ECG Image Dataset for Classification* (Kaggle).
* **Volume:** 100+ imagens no formato `.png` / `.jpg`.
* **Classes Mapeadas:** Traçados de ECG com elevação do segmento ST, sobrecarga ventricular (Hipertrofia - HYP), arritmias e sequelas de infarto antigo.
* **Aplicações em VC:** Redes Neurais Convolucionais (CNNs) para detecção de anomalias visuais e identificação de bordas/picos nos exames gráficos.

---

## Links Públicos para Acesso aos Dados

Em conformidade com os requisitos de entrega, os conjuntos completos de dados numéricos, textuais e visuais estão hospedados na nuvem sob acesso público:

* **[INSIRA_AQUI_O_LINK_PÚBLICO_DO_SEU_GOOGLE_DRIVE_OU_ONEDRIVE]**

---

## Governança de Dados, Viés e LGPD

O desenvolvimento da base do CardioIA segue os princípios formais de Governança de IA (NIST AI RMF e DAMA-DMBOK2):

* **Privacidade e LGPD:** Todas as bases públicas utilizadas (*PhysioNet*, *Kaggle*, *SciELO*) passaram por processos rigorosos de anonimização na origem, eliminando qualquer dado pessoal identificável (PII), em conformidade total com a Lei Geral de Proteção de Dados (LGPD).
* **Análise de Viés Algorítmico:** A base *PTB-XL* apresenta origem predominantemente europeia. Para aplicação no ecossistema de saúde brasileiro (SUS-SP), a etapa de modelagem prevê técnicas de ajustamento (*fine-tuning*) e calibração demográfica para evitar distorções no diagnóstico da população local.
* **Cadeia Evolutiva D-I-C-I:**
  * **Dado:** Métricas brutas de creatinina, pressão arterial e pixels das imagens de ECG.
  * **Informação:** Cálculo da probabilidade de risco (ex.: "Paciente em Risco CKM Estágio 2 com 84% de probabilidade").
  * **Conhecimento:** Cruzamento do diagnóstico probabilístico com o arquivo `.txt` de diretrizes da SBC.
  * **Inteligência:** Recomendação automática de protocolo preventivo e alerta ao cardiologista.

---

## Estrutura do Repositório

```text
├── assets/
│   ├── diretriz_insuficiencia_cardiaca.txt
│   └── consenso_sindrome_cardiorrenal.txt
├── README.md