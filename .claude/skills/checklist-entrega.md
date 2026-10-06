---
name: checklist-entrega
description: Checklist completo de entrega da Fase 2 do CardioIA — verifica todos os critérios do enunciado
---

# Checklist de Entrega — Fase 2

Percorrer cada item, verificar o estado atual e reportar o que está ✅ ok, ⚠️ parcial ou ❌ ausente.

## Parte 1 — Extrator de Sintomas (C1)

```bash
cd fase2 && python -m pytest tests/test_extrator_golden.py tests/test_base_conhecimento.py -v 2>&1 | tail -20
python src/main.py 2>&1 | head -40
```

- [ ] `fase2/src/extrator_sintomas.py` — normalização + extração de conceitos e atributos
- [ ] `fase2/src/analisador_clinico.py` — ranqueamento por condição com score explicativo
- [ ] `fase2/knowledge_base/` — 5 CSVs: conceitos (≥21), expressoes (≥97), atributos (≥23), associacoes (≥28), fontes (≥7)
- [ ] Golden tests passando para RELATO 01 e RELATO 04
- [ ] `fase2/notebooks/01_mapa_conhecimento.ipynb` — demonstra extração nos 10 relatos
- [ ] Saída em PT-BR, UTF-8, sem traceback

## Parte 2 — Classificador de Risco (C2)

```bash
ls fase2/data/frases_risco.csv 2>/dev/null && python -c "
import sys; sys.path.insert(0,'fase2/src')
import pandas as pd
df = pd.read_csv('fase2/data/frases_risco.csv')
print(f'Total: {len(df)} | Teste manual: {len(df[df.particao==\"teste\"])} | Alto: {(df.situacao==\"alto risco\").mean():.0%}')
"
```

- [ ] `fase2/data/frases_risco.csv` — ≥200 frases, ≥40 teste manual, ≥35% por classe, sem templates no teste
- [ ] `fase2/data/LINHAGEM.md` — descreve origem, critérios e responsável pelo dataset
- [ ] `fase2/notebooks/02_classificador.ipynb` — TF-IDF + 3 modelos + CV + curvas + relatório
- [ ] Gates: recall_alto_risco ≥ 0.90 AND acuracia ≥ 0.80 no conjunto teste

## Análise de Vieses (C3)

```bash
cd fase2 && python -m pytest tests/test_comportamento.py -v 2>&1 | tail -20
```

- [ ] `fase2/data/casos_comportamento.csv` — ≥15 casos: negação, gênero, acento, coloquial, atípico
- [ ] `fase2/notebooks/03_analise_vieses.ipynb` — testes de comportamento + cruzamento com PNS 2013
- [ ] Negação documentada como xfail no SDD §7 (limitação conhecida)

## Harness e Ferramentas

```bash
cd fase2 && python -m pytest tests/ -v 2>&1 | tail -5
```

- [ ] `fase2/pytest.ini` com `xfail_strict = true`
- [ ] `fase2/requirements.txt` completo
- [ ] `.spec/SDD-fase2-nlp-triagem.md` — contratos, limitações, metas
- [ ] `.claude/hooks/validar_base_conhecimento.py` + `.claude/settings.json` — hook ativo
- [ ] `.github/workflows/ci-fase2.yml` — CI rodando pytest

## README e Documentação

```bash
head -30 README.md
head -30 fase2/README.md 2>/dev/null || echo "fase2/README.md ausente"
```

- [ ] `README.md` raiz — lista todos os integrantes com nome completo e RM
- [ ] Link para o vídeo de apresentação (YouTube/Drive)
- [ ] `fase2/README.md` — instruções de execução da Fase 2

## Aviso Clínico

- [ ] Todo notebook exportado contém o aviso:
  > ⚠️ AVISO CLÍNICO: Este sistema é um protótipo acadêmico e NÃO substitui avaliação médica. Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).

## Resumo final

Ao terminar o checklist, apresentar:
```
FASE 2 — STATUS DE ENTREGA
✅ Concluídos: X/Y itens
⚠️ Parciais: ...
❌ Ausentes: ...
Próxima ação prioritária: ...
```
