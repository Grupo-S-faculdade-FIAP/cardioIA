# CardioIA — Fase 4: Assistente Cardiológico Virtual (Visão Computacional)

> ⚠️ **AVISO CLÍNICO:** Este sistema é um protótipo acadêmico e **NÃO** substitui avaliação médica.

Protótipo que transforma **imagens de ECG** (dataset público) em classificação assistida por CNN, com pré-processamento documentado, comparação entre rede treinada do zero e Transfer Learning (VGG16) e demonstração interativa em Gradio.

## Integrantes

| Nome completo | RM |
|---|---|
| Caroline de Castro Corrêa | RM567255 |
| Enzo França Sader | RM566928 |
| Lucas Hideki Oliveira Koyama | RM566925 |
| Rodrigo Dias Figueiroa | RM567800 |
| Tiago Lindgren Curi | RM567016 |

## Onde a Fase 4 se encaixa no CardioIA

A **Fase 1** estruturou os dados (incluindo a amostra de 120 ECGs). A **Fase 2** aplicou NLP e classificação de risco textual. A **Fase 3** acrescentou monitoramento IoT simulado. A **Fase 4** usa o **dataset Mendeley completo (~928 imagens, 4 classes)** para demonstrar visão computacional em exames cardíacos simulados/públicos.

A amostra versionada em `assets/imagens_ecg/` (120 imagens) **permanece intacta**. O conjunto completo fica em `fase4/data/imagens_ecg_completo/` (fora do Git).

## Onde está cada entregável

| Critério do enunciado | Arquivo |
|---|---|
| Notebook de pré-processamento | [`notebooks/01_preprocessamento.ipynb`](notebooks/01_preprocessamento.ipynb) |
| Relatório curto (1–2 páginas) | [`docs/relatorio_preprocessamento.md`](docs/relatorio_preprocessamento.md) |
| Notebook CNN + Transfer Learning + métricas | [`notebooks/02_cnn_classificacao.ipynb`](notebooks/02_cnn_classificacao.ipynb) |
| Prints / figuras de avaliação | [`docs/evidencias/`](docs/evidencias/) |
| Protótipo de apresentação | célula **Gradio** no notebook 02 |
| Linhagem do dataset | [`data/imagens_ecg_completo_LINHAGEM.md`](data/imagens_ecg_completo_LINHAGEM.md) |

## Dataset

| Item | Valor |
|---|---|
| Fonte | Mendeley — *ECG Images dataset of Cardiac Patients* v2 |
| DOI | [10.17632/gwbz3fsgp8.2](http://dx.doi.org/10.17632/gwbz3fsgp8.2) |
| Licença | CC BY 4.0 |
| Classes | `Normal`, `Infarto_Miocardio`, `Historico_Infarto_Miocardio`, `Batimento_Anormal` |
| Volume | 928 JPGs (~615 MB) |
| Split | 70% treino / 15% validação / 15% teste, estratificado, `seed=42` (648 / 140 / 140) |

## Resultados no teste (seed=42)

| Modelo | Acurácia | Precisão macro | Recall macro | F1 macro |
|---|---:|---:|---:|---:|
| CNN do zero | 0,307 | 0,077 | 0,250 | 0,117 |
| **VGG16 (Transfer Learning)** | **0,750** | **0,783** | **0,753** | **0,748** |

A CNN simples colapsou para a classe majoritária no teste (limitação esperada com laudos 224×224 e pouca capacidade). O **VGG16 com fine-tune leve** foi o modelo selecionado para o Gradio. Figuras: [`docs/evidencias/`](docs/evidencias/).

## Como executar

### Local

```bash
pip install -r fase4/requirements.txt

# 1) Baixar o dataset completo (~615 MB; idempotente)
python fase4/data/baixar_ecg_mendeley.py

# 2) Pré-processar e materializar splits
python fase4/src/pipeline_imagens.py

# 3) Treinar CNN + VGG16 e gravar métricas/evidências (alternativa headless aos notebooks)
python fase4/src/treinar_e_avaliar.py

# 4) Ou abrir os notebooks (Colab com GPU recomendado para a Parte 2)
jupyter notebook fase4/notebooks/
```

### Google Colab

1. Faça upload desta pasta `fase4/` (ou clone o repositório).
2. Abra `01_preprocessamento.ipynb` e execute todas as células (a primeira configura paths e baixa o dataset se necessário).
3. Abra `02_cnn_classificacao.ipynb` com **GPU** habilitada, treine os dois modelos e lance o Gradio.

## Arquitetura do pipeline

```text
Mendeley API ──► imagens_ecg_completo/<classe>/*.jpg
                      │
                      ▼
            pipeline_imagens.py
            (RGB, 224×224, [0,1], split 70/15/15)
                      │
                      ▼
              data/processado/{treino,validacao,teste}
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   CNN do zero              VGG16 (TL)
          │                       │
          └───────────┬───────────┘
                      ▼
            métricas + matriz de confusão
                      │
                      ▼
                 Gradio (demo)
```

## Estrutura de pastas

```text
fase4/
  README.md
  requirements.txt
  data/
    baixar_ecg_mendeley.py
    imagens_ecg_completo_LINHAGEM.md
    imagens_ecg_completo/     # gitignored
    processado/               # gitignored
  notebooks/
    01_preprocessamento.ipynb
    02_cnn_classificacao.ipynb
  docs/
    relatorio_preprocessamento.md
    evidencias/
  src/
    pipeline_imagens.py
  models/                     # pesos .keras (gitignored)
```
