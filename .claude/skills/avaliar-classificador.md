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

2. Rodar o harness de avaliação:

```python
# Em fase2/
import sys; sys.path.insert(0, 'src')
from avaliacao import executar
import json, pathlib

relatorio = executar("todos", pasta_saida=pathlib.Path("reports"))
print(json.dumps(relatorio, indent=2, ensure_ascii=False))
```

Ou via pytest para todos os testes de avaliação:

```bash
cd fase2 && python -m pytest tests/test_avaliacao.py -v --tb=short
```

3. Interpretar o relatório JSON gerado em `fase2/reports/metricas_todos.json`:

   | Campo               | O que verificar                                     |
   |---------------------|-----------------------------------------------------|
   | `modelo_escolhido`  | Qual modelo venceu (logreg / arvore / naive_bayes)  |
   | `metricas_teste`    | `recall_alto_risco` ≥ 0.90 e `acuracia` ≥ 0.80     |
   | `violacoes`         | Lista vazia = passou os gates; senão, listar erros  |
   | `comportamento`     | Taxa de acerto por tipo (negacao, genero, acento…)  |
   | `cv_treino`         | Média e desvio de recall na validação cruzada       |

4. Apresentar um resumo em PT-BR:
   - Modelo escolhido e por quê (recall CV no treino)
   - Métricas no conjunto teste (recall, acurácia, precisão)
   - Se passou ou não os gates — se não, o que está abaixo da meta
   - Comportamento: tipos que falharam (especialmente negação, que é xfail conhecido)
   - Próximos passos se houver violações

## Metas (metas_avaliacao.json)

```json
{"recall_alto_risco": 0.90, "acuracia": 0.80}
```

Recall é a métrica primária: falso negativo em triagem cardíaca = erro clínico grave.
