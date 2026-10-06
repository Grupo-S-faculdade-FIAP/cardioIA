# SDD — Fase 2: Extração de Sintomas (NLP) e Triagem de Risco

| | |
|---|---|
| **Projeto** | CardioIA — Fase 2 (Diagnóstico Automatizado — IA no Estetoscópio Digital) |
| **Componentes** | C1 `fase2/src/` (extrator + base de conhecimento) · C2 classificador de risco TF-IDF · C3 análise de vieses |
| **Harness de verificação** | `fase2/tests/` (pytest) + `fase2/src/avaliacao.py` (avaliação e metas) |
| **Metas numéricas** | `fase2/config/metas_avaliacao.json` |
| **Status** | C1 implementado (v1.1, Enzo) · C2 e C3 especificados, não implementados |
| **Última revisão** | 2026-10-06 |

> Este documento é a fonte de verdade do comportamento esperado. **Mudou o comportamento? Atualize este SDD primeiro**, depois os testes, depois o código.

---

## 1. Objetivo

1. **C1 — Extração:** ler relatos livres de pacientes, identificar conceitos clínicos e contexto, e sugerir condições possíveis com base na base de conhecimento (Parte 1 do enunciado).
2. **C2 — Triagem:** classificar frases curtas de sintomas em `alto risco` / `baixo risco` com TF-IDF + modelo do scikit-learn (Parte 2 do enunciado).
3. **C3 — Vieses:** medir onde C1 e C2 falham de forma sistemática (negação, gênero gramatical, linguagem coloquial, apresentações atípicas) e relacionar com dados reais da Fase 1 (PNS 2013).

O sistema é **educacional e de apoio à decisão**. Nenhuma saída é diagnóstico.

## 2. Requisitos e rastreabilidade

| ID | Requisito | Critério da rubrica (pts) | Artefato | Verificação |
|---|---|---|---|---|
| R1 | 10 relatos com sintoma, início e impacto na rotina | Relatos e mapa (2) | `fase2/data/relatos_pacientes.txt` | `test_extrator_golden.py::test_dez_relatos` |
| R2 | Mapa sintoma → condição íntegro e rastreável a fontes | Relatos e mapa (2) | `fase2/knowledge_base/*.csv` | `test_base_conhecimento.py` |
| R3 | Mapa também no formato do enunciado (`sintoma_1,sintoma_2,doenca_associada`) | Relatos e mapa (2) | `fase2/knowledge_base/mapa_conhecimento.csv` (derivado) | pendente — Etapa A |
| R4 | Extrator encontra os conceitos esperados nos 10 relatos | Extração funcional (2) | `fase2/src/` | `test_extrator_golden.py` |
| R5 | Extrator sugere **uma** condição principal por relato | Extração funcional (2) | `fase2/src/` | `test_extrator_golden.py` (xfail estrito até Etapa A) |
| R6 | Extrator respeita negação ("não sinto dor no peito") | Extração funcional (2) | `fase2/src/extrator_sintomas.py` | `test_comportamento.py` (xfail estrito até Etapa A) |
| R7 | Dataset de risco cumpre o contrato da §4 | Dataset simples (1) | `fase2/data/frases_risco.csv` + `LINHAGEM.md` | `test_contrato_dataset.py` |
| R8 | Classificador cumpre as metas da §5 no teste manual | Classificador (2) | `fase2/notebooks/02_classificador_risco.ipynb` | `test_avaliacao.py::test_metas_dataset_real` + CI |
| R9 | Notebooks executam do início ao fim sem erro | Classificador (2) / Documentação (1) | `fase2/notebooks/*.ipynb` | CI (`nbconvert --execute`) |
| R10 | Vieses medidos e discutidos | Classificador (2) | `fase2/notebooks/03_analise_vieses.ipynb` | relatório de comportamento (§6) |
| R11 | README completo, integrantes + RM, link do vídeo | Documentação (1) + Vídeo (2) | `README.md`, `fase2/README.md` | skill `checklist-entrega` |

## 3. Contrato da base de conhecimento (C1)

Verificado por `fase2/tests/test_base_conhecimento.py`. Qualquer violação quebra a CI.

1. Todo CSV tem o mesmo número de colunas em todas as linhas (sem vírgula sobrando).
2. IDs únicos e no padrão: `S###` (conceito), `E###` (expressão), `A###` (atributo), `AS###` (associação), `F###` (fonte).
3. Integridade referencial: `expressoes.conceito_id` e `associacoes.conceito_id` existem em `conceitos`; cada `fonte_id` (separado por `|`) existe em `fontes`; cada `atributos_relevantes` existe em `atributos`.
4. Todo conceito tem ≥ 1 expressão e ≥ 1 associação; toda fonte é usada por ≥ 1 associação.
5. Nenhuma expressão normalizada (minúsculas, sem acento/pontuação) aparece em dois conceitos diferentes — evita ambiguidade na extração.
6. Campos obrigatórios não vazios; todo atributo tem ≥ 1 gatilho.
7. Associações vêm de fonte (`fontes.csv`); expressões com `origem_expressao=simulada` **não** são citação científica.

## 4. Contrato do dataset de risco (C2)

Arquivo: `fase2/data/frases_risco.csv`, UTF-8, verificado por `fase2/src/contrato_dataset.py`.

| Coluna | Valores | Observação |
|---|---|---|
| `frase` | texto não vazio | relato curto em 1ª pessoa, PT-BR |
| `situacao` | `alto risco` \| `baixo risco` | nome exigido pelo enunciado |
| `origem` | `manual` \| `template` | `template` = gerada a partir da base de conhecimento |
| `particao` | `treino` \| `teste` | definida no arquivo, não sorteada no notebook |

Regras:
- **Teste só com frases manuais.** Frases de template reproduzem as regras de rotulagem; avaliar nelas infla a métrica (circularidade).
- **Sem duplicata** após normalização em todo o arquivo (impede vazamento treino → teste).
- Tamanho mínimo: 200 frases; teste com ≥ 40 frases.
- Cada classe com ≥ 35% no arquivo inteiro e no teste.
- O teste **nunca** é usado para treinar, escolher hiperparâmetro ou escolher modelo — isso é feito por validação cruzada no treino.
- Acompanha `fase2/data/frases_risco_LINHAGEM.md`: como foi gerado, por quem, critério de rótulo, contagens.

### 4.1 Critério de rótulo (proposta — pendente de validação clínica pela Dra. Fernanda Fassina)

`alto risco` = presença de **sinal de alarme** que, numa triagem, pede atendimento prioritário:

| # | Sinal de alarme | IDs na base |
|---|---|---|
| 1 | Dor/desconforto torácico **com** qualquer um: em repouso, não melhora com repouso, início súbito, duração > 20 min, irradiação, sudorese, náusea/vômito, tontura/síncope, padrão em piora (crescendo) | S013 + (A005, A007, A009, A012, A013–A018, S014, S015, S016, S017, S018, A011, A021–A023) |
| 2 | Síncope (perda de consciência) | S018 |
| 3 | Falta de ar em repouso, súbita, ou que desperta do sono | S001 + (A005, A009) · S003 |
| 4 | Equivalente anginoso / apresentação atípica: sudorese + náusea, ou cansaço súbito intenso com mal-estar, mesmo sem dor no peito | S014 + S015 · S004 + A009 |

`baixo risco` = sintomas leves, estáveis há semanas/meses, sem sinal de alarme, ou sintoma explicitamente negado. **Baixo risco não significa ausência de doença** — significa prioridade menor na fila.

## 5. Contrato de avaliação (C2)

Implementado em `fase2/src/avaliacao.py`; metas em `fase2/config/metas_avaliacao.json`.

- Vetorização: `TfidfVectorizer` com o mesmo `normalizar_texto` do extrator (minúsculas, sem acento), unigramas + bigramas.
- Modelos comparados: Regressão Logística, Árvore de Decisão, Naive Bayes Multinomial. Seed fixa `42`.
- Seleção de modelo: validação cruzada estratificada 5-fold **apenas no treino**.
- Métricas reportadas no teste manual: acurácia, precisão / recall / F1 da classe `alto risco`, matriz de confusão.
- **Métrica principal: recall de `alto risco`.** Em triagem, mandar um paciente grave para o fim da fila (falso negativo) é o erro caro.
- Metas (gate — a CI falha se não cumprir): `recall_alto_risco ≥ 0,90` e `acuracia ≥ 0,80` no teste manual.
- Saída: `fase2/reports/metricas_<modelo>.json`, versionado, para comparar execuções.

## 6. Testes de comportamento e vieses (C3)

Casos em `fase2/data/casos_comportamento.csv` (`caso_id,tipo,frase,risco_esperado`). São **relatados, não usados como gate** — servem para expor vieses, não para serem "decorados".

| Tipo | O que testa | Exemplo |
|---|---|---|
| `negacao` | sintoma negado não conta | "Não sinto dor no peito, só um cansaço leve no fim do dia" → baixo |
| `genero` | trocar "cansado"/"cansada" não muda o risco | mesmo relato nas duas formas → mesmo rótulo |
| `acento` | texto sem acento tem o mesmo resultado | "pressao no peito" = "pressão no peito" |
| `coloquial` | linguagem popular | "uma agonia no peito que não passa" → alto |
| `atipico` | apresentação atípica (mais comum em mulheres, idosos, diabéticos) | "suor frio, enjoo e um cansaço que veio do nada" → alto |

Ligação com a Fase 1: o notebook de vieses cruza `Sintoma_Dor_Desconforto_Peito` × `Sexo` / `Raca_Etnia` / `Regiao` × `Infarto_Miocardio` em `data/processed/pns_ckm_estagios_2013.csv` para mostrar, com dado brasileiro real, que "dor no peito" não representa todos os grupos igualmente.

## 7. Limitações conhecidas (C1 v1.1)

Rastreadas como `xfail(strict=True)` nos testes — quando forem corrigidas, o teste passa a falhar e obriga a remover o `xfail` e atualizar esta seção.

- Sem tratamento de negação (R6).
- Sem sugestão única: empate IAM × Angina no RELATO 07; empate triplo no RELATO 08 (R5).
- Pontuação soma +1 para qualquer relação, sem peso por `tipo_relacao` — sintomas compartilhados (dispneia) geram ruído.
- Nome de condição inconsistente: `Insuficiência Cardíaca / contexto cardiorrenal` vs `Insuficiência Cardíaca`.

## 8. Como reproduzir

```bash
pip install -r fase2/requirements.txt
pytest fase2                                   # harness completo
python fase2/src/main.py                       # C1 nos 10 relatos
python fase2/src/avaliacao.py --modelo todos   # C2 (requer frases_risco.csv)
```
