# CardioIA — Fase 2

## Diagnóstico Automatizado — IA no Estetoscópio Digital

Esta pasta contém o desenvolvimento da **Fase 2 do projeto CardioIA**, desenvolvido no curso de Inteligência Artificial da FIAP.

Nesta etapa, o projeto utiliza técnicas de **Processamento de Linguagem Natural (NLP)** para analisar relatos textuais de pacientes, identificar sintomas e características clínicas e relacioná-los a possíveis condições cardiovasculares com base em uma base de conhecimento estruturada.

> O CardioIA é um projeto acadêmico de apoio à decisão e não realiza diagnóstico médico definitivo.

---

## Estrutura

```text
fase2/
├── data/
│   └── relatos_pacientes.txt
│
├── knowledge_base/
│   ├── conceitos.csv
│   ├── expressoes.csv
│   ├── atributos.csv
│   ├── associacoes.csv
│   ├── fontes.csv
│   └── README.md
│
├── src/
│   ├── carregador_base.py
│   ├── extrator_sintomas.py
│   ├── analisador_clinico.py
│   └── main.py
│
├── notebooks/
├── tests/
└── README.md
