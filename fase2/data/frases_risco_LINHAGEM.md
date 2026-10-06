# Linhagem — frases_risco.csv

Dataset da **Parte 2** (classificador de risco por TF-IDF). Gerado em 2026-10-06 por:

```bash
python fase2/src/gerar_frases_risco.py     # seed 42, base de conhecimento v1.2
```

| Arquivo | SHA-256 |
|---|---|
| `frases_risco.csv` (gerado) | `584cf3c9e99a05ae9b9dd0af92d1e37a64477e6d4f46cc1fc118b6201f75df48` |
| `frases_manuais.csv` (fonte) | `4d4d8dcc7b6fb4e8e516054f3214c4ae1f5629e36e57a701a67c770ffe07dd58` |
| linhas de teste (ver `config/teste_congelado.json`) | `e8288963738a08216d0b5d4036116ffd8cd9de9936f82dd750c6b6c51596105f` |

> **Nenhum dado real de paciente.** Todas as frases são sintéticas.

## Origem

```
frases_manuais.csv (140) ─┐
                          ├─► gerar_frases_risco.py ─► frases_risco.csv (320)
knowledge_base v1.2 ──────┤      frases manuais entram como estão
seed 42 ──────────────────┘      + 180 templates sorteados, só no treino
```

- **Manuais (140):** escritas uma a uma, sem gerador, em linguagem variada: formal e coloquial ("tô", "pro", "apaguei"), voz feminina (17) e masculina (18), 6 relatos de acompanhante ("meu pai está com…"), 2 frases de teste escritas sem acento de propósito, apresentações atípicas (idosos, suor frio + náusea sem dor) e casos-armadilha (dor no peito musculoesquelética, "pressão" no sentido de pressão arterial, negações). **Todo o conjunto de teste vem daqui.**
- **Templates (180):** combinações de expressões da base de conhecimento (dor torácica, síncope, dispneia) com gatilhos de alarme já cadastrados (irradiação, repouso, duração > 20 min…) para alto risco, e com contextos leves, queixas não cardíacas ou negações para baixo risco. O rótulo vem do template. Um teste garante que a linha de base por regras (`classificador_regras.py`) dá o mesmo rótulo a todos os 180.

## Autoria

- **Frases manuais:** redigidas por Claude (assistente de IA) a pedido da equipe em 2026-10-06. **A revisão humana pela equipe está pendente.**
- **Critério de rótulo:** SDD Fase 2 §4.1. **A validação clínica pela Dra. Fernanda Fassina (CRM-SP 169944) está pendente.**

## Rótulos

| Situação | Critério | Teste (manual) | Treino (manual) | Treino (template) | Total |
|---|---|---:|---:|---:|---:|
| alto risco | A1 dor torácica + sinal de alarme | 17 | 18 | 45 | 80 |
| alto risco | A2 síncope | 4 | 7 | 15 | 26 |
| alto risco | A3 dispneia em repouso, súbita ou noturna | 5 | 7 | 15 | 27 |
| alto risco | A4 equivalente atípico | 4 | 8 | 15 | 27 |
| baixo risco | B1 sintoma leve e estável | 13 | 16 | 35 | 64 |
| baixo risco | B2 queixa não cardíaca | 13 | 16 | 35 | 64 |
| baixo risco | B3 alarme negado | 4 | 8 | 20 | 32 |
| | **Total** | **60** | **80** | **180** | **320** |

Classes balanceadas: 160 de alto risco e 160 de baixo risco, tanto no arquivo quanto no teste (30 × 30).

## Conjunto de teste congelado

O teste foi **congelado antes da primeira avaliação** (`fase2/config/teste_congelado.json`). Qualquer edição quebra o harness (`test_conjunto_de_teste_congelado`). Mudar o teste exige aprovação da equipe, revisão clínica, um novo hash e um registro abaixo.

## Registro de avaliações

| Data | Treino | Modelo (escolhido por validação cruzada) | Acurácia (teste) | Recall alto risco (teste) | Precisão alto risco (teste) | Mudanças depois |
|---|---|---|---:|---:|---:|---|
| 2026-10-06 | 260 frases (80 manuais + 180 templates) | Naive Bayes multinomial | 0,917 | 0,900 | 0,931 | nenhuma |

O recall ficou **exatamente** na meta (3 falsos negativos em 30). Os erros estão analisados nos notebooks 02 e 03. Não houve ajuste de dados nem de modelo depois de olhar o teste.

## Limitações conhecidas

- **Mesmo autor no treino e no teste.** Isso traz risco de semelhança de estilo, que tende a inflar a métrica. Recomendação: integrantes da equipe escreverem um segundo teste cego.
- **Templates artificiais.** Algumas frases soam pouco naturais ("…náusea, enquanto descansava"). Palavras que se repetem nos templates viram pistas espúrias para o TF-IDF: "só" aparece em todo template de negação, "depois do almoço" em templates de alto risco (ver notebook 03).
- **Negação × saco de palavras.** Os templates B3 ("Não tenho dor no peito nem falta de ar, só…") associam as palavras do sintoma à classe de baixo risco. O TF-IDF não enxerga negação.
- **Cobertura regional:** o português é coloquial do Sudeste, e vocabulário de outras regiões está sub-representado.
- **Rótulo binário:** baixo risco **não** significa ausência de doença. A angina estável, por exemplo, é baixo risco na fila de triagem, mas precisa de avaliação ambulatorial.
