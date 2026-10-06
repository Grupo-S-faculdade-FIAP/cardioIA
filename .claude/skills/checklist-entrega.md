---
name: checklist-entrega
description: Confere a entrega da Fase 2 do CardioIA contra a rubrica de 10 pontos do enunciado e lista pendências
---

# Checklist de Entrega — Fase 2

Percorrer cada item, verificar o estado **real** (rodar os comandos, não supor) e reportar ✅ ok, ⚠️ parcial ou ❌ ausente.

## 0. Harness (pré-condição de tudo)

```bash
cd fase2 && python -m pytest -q --no-header -p no:cacheprovider 2>&1 | tail -5
```

- [ ] Suíte verde; os únicos `xfail` são limitações documentadas no SDD §7
- [ ] Nenhum teste `skipped` por falta de `frases_risco.csv`

## 1. Relatos e mapa de conhecimento organizados — 2 pts

- [ ] `fase2/data/relatos_pacientes.txt` — 10 relatos com sintoma, início e impacto na rotina
- [ ] `fase2/knowledge_base/` — 5 CSVs normalizados + `README.md`
- [ ] `fase2/knowledge_base/mapa_conhecimento.csv` — formato `sintoma_1,sintoma_2,doenca_associada`, sincronizado (`python fase2/src/gerar_mapa_conhecimento.py` não gera diff)

## 2. Código de extração funcional — 2 pts

```bash
python fase2/src/main.py | tail -16
```

- [ ] `main.py` roda sem traceback, com acentos corretos, e termina no aviso clínico
- [ ] Os 10 relatos têm sugestão principal única e igual ao golden (`tests/golden/relatos_esperados.json`)
- [ ] `fase2/notebooks/01_extracao_sintomas.ipynb` executado, com saídas salvas

## 3. Dataset simples criado corretamente — 1 pt

```bash
cd fase2 && python -m pytest tests/test_contrato_dataset.py -q --no-header
```

- [ ] `fase2/data/frases_risco.csv` — colunas `frase,situacao` (+ `origem,particao`), ≥ 200 frases, ≥ 40 de teste manual, ≥ 35% por classe
- [ ] `fase2/data/frases_risco_LINHAGEM.md` — origem, autoria, critério de rótulo, contagens, limitações

## 4. Classificador treinado e testado corretamente — 2 pts

```bash
python fase2/src/avaliacao.py --modelo todos
```

- [ ] Metas cumpridas: `recall_alto_risco ≥ 0,90` e `acuracia ≥ 0,80` no teste manual
- [ ] `fase2/reports/metricas_todos.json` versionado e coerente com a execução atual
- [ ] `fase2/notebooks/02_classificador_risco.ipynb` executado: TF-IDF, comparação de modelos, matriz de confusão, termos mais influentes, análise de erros
- [ ] `fase2/notebooks/03_analise_vieses.ipynb` executado: comportamento (negação, gênero, acento, coloquial, atípico) + cruzamento com PNS 2013

## 5. Documentação e repositório público — 1 pt

- [ ] `README.md` da raiz descreve a Fase 2 (não só a Fase 1) e aponta para `fase2/`
- [ ] `fase2/README.md` com instruções de execução, resultados e limitações
- [ ] Integrantes com **nome completo e RM**
- [ ] Repositório **público** no GitHub (`gh repo view --json visibility`)
- [ ] CI (`.github/workflows/ci-fase2.yml`) verde no último push

## 6. Vídeo — 2 pts

- [ ] Vídeo de até 4 min no YouTube como **não listado**
- [ ] Link no README do repositório

## 7. Governança

- [ ] Todo notebook e README público contém o aviso:
  > ⚠️ AVISO CLÍNICO: Este sistema é um protótipo acadêmico e NÃO substitui avaliação médica. Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).
- [ ] Pendências de validação clínica listadas (SDD §7) e comunicadas à Dra. Fernanda

## Resumo final

```
FASE 2 — STATUS DE ENTREGA
✅ Concluídos: X/Y itens   (pontos garantidos: N/10)
⚠️ Parciais: ...
❌ Ausentes: ...
Próxima ação prioritária: ...
```
