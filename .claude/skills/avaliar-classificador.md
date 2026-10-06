---
name: avaliar-classificador
description: Executa o harness de avaliação do classificador de risco (SDD §5) e gera relatório
---

# Avaliar Classificador

Executa `fase2/src/avaliacao.py` com o dataset real e reporta métricas, comportamento e conformidade com as metas.

## Pré-condição

- `fase2/data/frases_risco.csv` deve existir e passar o contrato do dataset (SDD §4).
- Se não existir, avisar: "frases_risco.csv ainda não criado — criar o dataset primeiro (Etapa B do plano)."

## Passos

1. Verificar existência do dataset:

```bash
ls fase2/data/frases_risco.csv 2>/dev/null && echo "ok" || echo "ausente"
```

2. Rodar o harness de avaliação (grava `fase2/reports/metricas_todos.json`; sai com código 1 se o contrato ou as metas falharem):

```bash
python fase2/src/avaliacao.py --modelo todos
cd fase2 && python -m pytest tests/test_avaliacao.py -v --tb=short
```

3. Interpretar o relatório JSON:

   | Campo               | O que verificar                                     |
   |---------------------|-----------------------------------------------------|
   | `modelo_escolhido`  | Qual modelo venceu (logreg / arvore / naive_bayes)  |
   | `validacao_cruzada` | Média e desvio de recall/acurácia no treino (5-fold) |
   | `teste`             | `recall_alto_risco` ≥ 0.90 e `acuracia` ≥ 0.80; matriz de confusão |
   | `violacoes`         | Lista vazia = passou os gates; senão, listar erros  |
   | `comportamento`     | Taxa de acerto por tipo (negacao, genero, acento…) e falhas |

4. Apresentar um resumo em PT-BR:
   - Modelo escolhido e por quê (recall na validação cruzada do treino)
   - Métricas no conjunto teste (recall, acurácia, precisão)
   - Se passou ou não os gates — se não, o que está abaixo da meta
   - Comportamento: tipos que falharam e o que isso revela de viés
   - Próximos passos se houver violações

## Regra de ouro

Meta não cumprida **não** autoriza mexer no conjunto de teste nem escolher modelo olhando o teste. Corrija o treino (mais frases, frases mais variadas) ou o modelo, valide por validação cruzada e só então rode o teste de novo — registrando a rodada no `frases_risco_LINHAGEM.md`.

## Metas (metas_avaliacao.json)

```json
{"recall_alto_risco": 0.90, "acuracia": 0.80}
```

Recall é a métrica primária: falso negativo em triagem cardíaca = erro clínico grave.
