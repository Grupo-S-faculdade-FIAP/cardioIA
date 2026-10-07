# Relatório Técnico — CardioIA, Fase 2: IA no Estetoscópio Digital

| | |
|---|---|
| **Projeto** | CardioIA — Diagnóstico e Alerta Precoce da Síndrome Cardiorrenal-Metabólica |
| **Curso** | Inteligência Artificial, FIAP |
| **Supervisão clínica** | Dra. Fernanda Fassina (Cardiologista e Clínica Geral, CRM-SP 169944) |
| **Escopo deste relatório** | Estado do projeto ao final da Fase 2 — NLP clínico, base de conhecimento, classificador de risco e análise de vieses |
| **Integrantes** | Caroline de Castro Corrêa (RM567255) · Enzo França Sader (RM566928) · Lucas Hideki Oliveira Koyama (RM566925) · Rodrigo Dias Figueiroa (RM567800) · Tiago Lindgren Curi (RM567016) |
| **Última revisão** | 2026-10-07 |

---

## 1. Resumo executivo

A Fase 2 do CardioIA constrói o **estetoscópio digital**: um sistema capaz de ler o que o paciente diz em linguagem natural e identificar se há risco cardíaco. Enquanto a Fase 1 trabalhou com dados numéricos estruturados (biomarcadores, medidas, estágios CKM), esta fase trabalha com texto — a forma mais comum de comunicação entre paciente e sistema de saúde.

Nesta fase, o projeto:

1. Construiu uma **base de conhecimento clínica normalizada** em 5 tabelas inter-relacionadas, cobrindo 21 conceitos clínicos e 99 formas de expressão de sintomas em português, com rastreabilidade completa a 7 fontes científicas (SBC, AHA, Ministério da Saúde).
2. Implementou um **extrator de sintomas** com tratamento de negação (NegEx simplificado), pontuação explicável por tipo de relação clínica e sugestão única de condição principal — acertando 10/10 casos do gabarito, incluindo o RELATO 08 (empate triplo resolvido por peso diferencial de tipo de relação).
3. Criou e avaliou um **classificador de risco** TF-IDF com 3 modelos scikit-learn, escolhido exclusivamente por validação cruzada no conjunto treino: Naive Bayes atingiu **acurácia 0,917** e **recall de alto risco 0,900** no teste congelado — exatamente na meta primária de triagem.
4. **Mediu 6 vieses sistematicamente** — negação, gênero gramatical, acento/ortografia, linguagem coloquial, apresentações atípicas e distribuição por sexo com dado real da PNS 2013 — e documentou mitigações e limitações residuais.
5. Construiu um **harness de testes automatizados** (150 testes pytest) com contratos do SDD, gabarito congelado e CI no GitHub Actions — mais 4 agentes especializados de IA para revisão clínica, red-team, operação autônoma e rastreabilidade de decisões.

O resultado é um protótipo funcional e auditável: cada decisão de pesos, cada escolha de modelo e cada limitação conhecida estão registrados em documentos versionados, não apenas na memória de quem construiu.

---

## 2. Contexto clínico e motivação

A Fase 1 respondeu: "este paciente está em que estágio de CKM?" — a partir de exames laboratoriais e medidas objetivas. A Fase 2 responde uma pergunta anterior e mais comum na prática clínica: **"o que este paciente está relatando sugere risco cardíaco?"**

O problema concreto que motiva esta fase: a maioria dos sistemas de triagem digital, chatbots de saúde e formulários de pré-consulta ignora o que o paciente diz em suas próprias palavras. Quando processam texto, usam modelos genéricos de linguagem que não conhecem a diferença entre "falta de ar ao deitar" (ortopneia de IC) e "falta de ar ao correr" (condicionamento físico) — nem reconhecem que "fico sem ar quando me deito" e "sleeping position gives me shortness of breath" são o mesmo sintoma em registros diferentes.

Dois achados da Fase 1 ampliam a motivação:

- **53,6% da amostra** PNS 2013 tinha "peso normal" pelo IMC mas "obesidade central" pela RCE — ou seja, risco cardiometabólico real invisível ao exame mais comum. Um sistema de triagem textual pode capturar os sintomas desse grupo antes mesmo do exame.
- A Dra. Fernanda Fassina identificou que **sintomas atípicos de IAM em mulheres** (náusea, fadiga, mal-estar sem dor torácica clássica) são causa frequente de diagnóstico tardio no ambulatório. A Fase 2 trata isso explicitamente via critério A4 do dataset e teste contrafactual de gênero.

---

## 3. Arquitetura do sistema NLP

O sistema tem dois componentes principais, mais uma camada de análise:

```
Componente 1 (C1) — Extração e sugestão          Componente 2 (C2) — Triagem de risco
  ┌─────────────────────────────────────┐            ┌──────────────────────────────────┐
  │ relato livre do paciente            │            │ frase curta de sintoma           │
  │     ↓                               │            │     ↓                            │
  │ normalização (minúsculas, acento)   │            │ TF-IDF (unigramas + bigramas)    │
  │     ↓                               │            │     ↓                            │
  │ expressões → conceitos clínicos     │            │ Naive Bayes                      │
  │     ↓                               │            │     ↓                            │
  │ NegEx simplificado (negação)        │            │ alto risco / baixo risco         │
  │     ↓                               │            └──────────────────────────────────┘
  │ atributos de contexto               │
  │ (esforço, repouso, irradiação…)     │    Componente 3 (C3) — Vieses
  │     ↓                               │    ┌──────────────────────────────────────────┐
  │ associações KB (com tipo e fonte)   │    │ comportamento por tipo (15 casos)        │
  │     ↓                               │    │ negação · gênero · acento · coloquial    │
  │ pontuação explicável                │    │ atípico · distribuição real (PNS 2013)   │
  │     ↓                               │    └──────────────────────────────────────────┘
  │ sugestão principal (ou inconclusivo)│
  └─────────────────────────────────────┘
```

C1 é uma abordagem **baseada em regras e conhecimento** — explícita, auditável, rastreável a fontes. C2 é **aprendizado de máquina** sobre o que C1 não consegue capturar com regras (variações livres de linguagem). C3 audita os dois.

A separação é intencional: um sistema de triagem clínica precisa ser explicável. O extrator C1 sempre devolve quais evidências pontuaram e por quê; o classificador C2 é caixa-cinza (TF-IDF permite ver os termos mais influentes), não caixa-preta.

---

## 4. Parte 1 — Base de conhecimento e extração de sintomas

### 4.1 A base de conhecimento

A base de conhecimento ([`fase2/knowledge_base/`](fase2/knowledge_base/)) é um grafo de entidades em 5 tabelas CSV normalizadas, ligadas por IDs imutáveis:

| Tabela | O que guarda | Linhas |
|---|---|---:|
| `conceitos.csv` | Sintomas e condições clínicas | 21 |
| `expressoes.csv` | Formas como o paciente diz cada conceito | 99 |
| `atributos.csv` | Contexto: esforço, repouso, irradiação, duração… | 23 |
| `associacoes.csv` | Conceito → condição, com tipo de relação e fonte | 29 |
| `fontes.csv` | Diretrizes e referências científicas | 7 |

A tabela `mapa_conhecimento.csv` é uma **vista derivada** no formato do enunciado (`sintoma_1, sintoma_2, doença_associada`) — gerada por script e nunca editada à mão, com 82 linhas.

A separação entre **expressão** ("fico sem ar") e **conceito clínico** ("Dispneia") é o núcleo do design: ela permite que a base cresça independentemente — novas formas de dizer o mesmo sintoma não exigem novas regras de associação. A manutenção é localizada e rastreável.

As 7 fontes referenciadas são instituições reconhecidas (SBC, AHA, Ministério da Saúde, ESC), com URL registrada. Toda associação clínica tem um `fonte_id` obrigatório — não há associação sem rastreabilidade à literatura.

### 4.2 O extrator — decisões de projeto

**Por que pontuação por tipo de relação, não por frequência?**

Uma abordagem ingênua somaria 1 ponto por sintoma encontrado. O problema: "falta de ar" é sintoma típico de IC e de IAM — uma frase com três sintomas de IC e um de IAM somaria empate com qualquer outra combinação. A solução foi ponderar pelo tipo de relação clínica:

| Tipo de relação | Peso |
|---|---:|
| `manifestacao_principal` | 3 |
| `sintoma_tipico`, `manifestacao_contextual` | 2 |
| demais tipos (`fator_risco`, `comorbidade`…) | 1 |

Isso replica a heurística do médico: dor torácica irradiante pesa mais que náusea associada ao quadro. A pontuação **ordena hipóteses** e não é probabilidade.

**Negação (NegEx simplificado):**

"Não sinto dor no peito" não deve contar como presença de dor torácica. O extrator aplica uma janela de negação: qualquer conceito que apareça dentro de N tokens após uma expressão negativa (`não sinto`, `sem`, `nunca tive`…) tem seu score zerado. Isso é tratado antes de qualquer outra pontuação.

**Sugestão única:**

O SDD exige que cada relato termine com uma única condição principal. Empate é resolvido pela soma de pontos de contexto (atributos); persistindo o empate, o sistema reporta "inconclusivo" em vez de escolher arbitrariamente — honestidade epistêmica sobre o que a base não consegue decidir.

### 4.3 Gabarito dos 10 relatos

Os 10 relatos sintéticos cobrem os quadros mais prevalentes em triagem CKM: Insuficiência Cardíaca (IC), IAM/Síndrome Coronariana Aguda (SCA) e Angina. O RELATO 08 é deliberadamente o mais difícil — edema periférico, oligúria e falta de ar, que cruzam IC e síndrome cardiorrenal:

| Relato | Quadro | Sugestão principal (pontos) | 2ª hipótese |
|---|---|---|---|
| 01 | Dispneia de esforço + cansaço | IC (7) | Angina (3) |
| 02 | Ortopneia | IC (7) | — |
| 03 | DPN (acorda sem ar) | IC (5) | — |
| 04 | Dor súbita, irradiação, suor frio, > 20 min | IAM/SCA (11) | Angina (5) |
| 05 | Desconforto, tontura, palidez | IAM/SCA (5) | Angina (4) |
| 06 | Dor ao esforço, melhora com repouso | Angina (6) | IAM/SCA (4) |
| 07 | Angina em crescendo, em repouso | IAM/SCA (8) | Angina (5) |
| 08 | Edema + oligúria + falta de ar + cansaço | IC (7) | Congestão cardiorrenal (5) |
| 09 | Ganho de peso, noctúria, tosse noturna | IC (6) | Angina (1) |
| 10 | Perda de apetite e peso, cansaço | IC (5) | Angina (1) |

**10/10 corretos no gabarito.** O RELATO 08 anteriormente empatava em três condições; o empate foi resolvido adicionando o peso diferencial de edema associado à IC (associação AS029, fonte F001) — decisão clínica documentada com pendência de validação da Dra. Fernanda (SDD §7, CDR a ser lavrado).

### 4.4 Contrato de paridade de gênero

A base original tinha expressões somente no masculino ("estava sentado", "mesmo estando parado"). Um contrato de paridade foi criado: toda expressão com adjetivo ou particípio flexionado em gênero exige o par do gênero oposto. Verificado por `test_base_conhecimento.py` e pelo teste contrafactual: **0 inversões de sugestão** ao trocar o gênero gramatical do relato.

---

## 5. Parte 2 — Classificador de risco (TF-IDF)

### 5.1 O dataset

[`fase2/data/frases_risco.csv`](fase2/data/frases_risco.csv): **320 frases**, balanceadas (160 alto risco, 160 baixo risco).

| Origem | Qtd | Usado em |
|---|---:|---|
| Manuais (escritas uma a uma) | 140 | Treino + **teste congelado** |
| Templates (gerados da base, seed 42) | 180 | Treino apenas |
| **Total** | **320** | — |
| — dos quais no teste congelado | 60 | Teste somente |

A separação entre manuais e templates é fundamental: templates reproduzem as regras de rotulagem (quem os gerou sabe o rótulo por construção), então avaliá-los infla as métricas artificialmente. O teste congelado usa **exclusivamente frases manuais** — as mais difíceis, com vozes variadas, linguagem coloquial e apresentações atípicas.

**Critério de rótulo explícito:** cada frase traz o código do critério clínico que justifica seu rótulo:

| Código | Critério | Direção |
|---|---|---|
| A1 | Dor torácica com sinal de alarme | Alto risco |
| A2 | Síncope / pré-síncope | Alto risco |
| A3 | Dispneia grave (repouso, ortopneia, DPN) | Alto risco |
| A4 | Equivalente atípico (equivalente de dor em mulheres, idosos) | Alto risco |
| B1 | Sintoma leve e estável, sem sinal de alarme | Baixo risco |
| B2 | Queixa não cardíaca | Baixo risco |
| B3 | Sinal de alarme presente mas explicitamente negado | Baixo risco |

### 5.2 Escolha do modelo

Três modelos foram comparados **exclusivamente no conjunto treino**, por validação cruzada de 5-fold com seed 42:

| Modelo | Acurácia CV (treino) | Recall alto risco CV | Acurácia (teste) | Recall alto risco (teste) |
|---|---:|---:|---:|---:|
| Regressão Logística | 0,965 ± 0,026 | 0,969 ± 0,038 | — | — |
| Árvore de Decisão | 0,892 ± 0,041 | 0,885 ± 0,024 | — | — |
| **Naive Bayes** | **0,969 ± 0,020** | **0,969 ± 0,029** | **0,917** | **0,900** |

Naive Bayes foi o modelo escolhido por ter o maior recall de alto risco na validação cruzada — a métrica primária, porque em triagem cardíaca o erro caro é mandar um paciente de alto risco para o fim da fila (falso negativo), não o contrário.

A Regressão Logística empatou na validação cruzada e superou o Naive Bayes no teste (recall 0,967). **Essa superioridade no teste não poderia ter sido usada para a escolha**: decidir pelo modelo depois de ver o conjunto de teste é data leakage disfarçado, invalida a avaliação e tornaria as métricas do teste não generalizáveis. O Naive Bayes foi escolhido antes de olhar o teste. Os erros da Regressão Logística no treino foram analisados no Notebook 02.

### 5.3 Resultado oficial no teste congelado

Fonte: [`fase2/reports/metricas_todos.json`](fase2/reports/metricas_todos.json) — arquivo versionado, resultado da última execução de `avaliacao.py --modelo todos`.

| Métrica | Valor | Meta (SDD) | Status |
|---|---:|---:|---|
| Recall alto risco | **0,900** | ≥ 0,90 | ✅ Atingida |
| Acurácia | **0,917** | ≥ 0,80 | ✅ Atingida |
| Precisão alto risco | 0,931 | — | — |
| F1 alto risco | 0,915 | — | — |

**Violações de contrato:** nenhuma (`"violacoes": []`).

**Matriz de confusão no teste (n=60):**

| | Predito: baixo risco | Predito: alto risco |
|---|---:|---:|
| **Real: baixo risco** | 28 (VP) | 2 (FP) |
| **Real: alto risco** | 3 (FN) | 27 (VP) |

Os 3 falsos negativos são frases de apresentação atípica (critério A4) analisadas termo a termo no Notebook 02. Os 2 falsos positivos são frases de baixo risco com vocabulário de alarme negado (B3) — o modelo não lida bem com negação via TF-IDF.

### 5.4 Linha de base por regras

O classificador de regras da Fase 1 (C1) também foi avaliado como linha de base:

| Sistema | Acurácia | Recall alto risco | Precisão alto risco |
|---|---:|---:|---:|
| **Naive Bayes (oficial)** | **0,917** | **0,900** | **0,931** |
| Regras C1 (linha de base) | 0,717 | 0,433 | 1,000 |

As regras têm **precisão perfeita** mas recall muito baixo: quando acertam, acertam com certeza; mas deixam passar dois em cada três casos de alto risco. A combinação regras + ML na validação cruzada mostrou recall de 0,977 — o melhor resultado observado, mas avaliado só no treino.

---

## 6. Vieses — medição e governança

### 6.1 Comportamento do classificador ML por tipo de frase

Resultado do `avaliacao.py` em `cases_comportamento.csv` (15 casos, 3 por tipo):

| Tipo | Acertos | Total | Taxa |
|---|---:|---:|---:|
| Negação | 3 | 3 | 1,00 |
| Gênero gramatical | 4 | 4 | 1,00 |
| Acento / variação ortográfica | 2 | 2 | 1,00 |
| Linguagem coloquial | 3 | 3 | 1,00 |
| Apresentação atípica | 3 | 3 | 1,00 |

**100% de acerto em todos os tipos** — resultado que reflete o conjunto de comportamento *atual*, não uma garantia de robustez geral. O conjunto tem 15 casos; o Notebook 03 analisa sistematicamente os limites.

### 6.2 Vieses encontrados na análise completa

| Viés | Evidência | Status da mitigação |
|---|---|---|
| Vocabulário de livro nas regras | Recall de 0,433 no teste; "apaguei", "agonia no peito" não reconhecidos | ML + vocabulário variado resolve |
| Negação no ML | "Não sinto aperto no peito" → P(alto risco) = 0,86 | Documentado; combinação regras+ML melhora recall |
| Pistas espúrias dos templates | "Comecei a sentir… agora" transforma dor de cabeça em alto risco | Documentado; próxima rodada diversifica os moldes |
| Gênero gramatical | Base original só tinha formas masculinas | Contrato de paridade + 0 inversões no teste contrafactual |
| Conjugação verbal | "acordei" ≠ "acordo"; recall das regras na dispneia grave: 1/5 | Documentado; lematização na Fase 3 |
| **Apresentação atípica (PNS 2013)** | 17% das mulheres com infarto relatam dor torácica vs. 26% dos homens | Critério A4 + frases atípicas; recall por sexo pendente com dados reais |

### 6.3 Conexão com os dados reais da Fase 1

O Notebook 03 cruza os achados do classificador com a PNS 2013. O dado mais relevante: entre os participantes da PNS que reportaram infarto (`Infarto=1`), a taxa de dor torácica autorreferida é **17% entre mulheres** e **26% entre homens** — evidência de que apresentações atípicas são, na prática, a apresentação mais comum em metade da população. O critério A4 do dataset (equivalente atípico) foi desenhado especificamente para esse grupo, mas o recall por sexo com dados reais ainda não foi calculado — limitação registrada no SDD §7.

---

## 7. Governança, dados sintéticos e LGPD

- **Nenhum dado real de paciente.** Os 10 relatos e as 320 frases do dataset são 100% sintéticos. A única base real usada é a PNS 2013 da Fase 1 (pública, desidentificada, LAI) — para análise epidemiológica dos vieses, não como dado de treinamento.

- **Autoria do dataset.** As 140 frases manuais foram redigidas com auxílio de IA generativa (Claude) e revisadas pela equipe. Não passaram por revisão clínica formal da Dra. Fernanda — limitação explicitamente documentada no README e no SDD §7. O ideal é a equipe produzir um segundo conjunto de teste cego, sem conhecimento dos critérios de rotulagem, para validação externa.

- **Conjunto de teste congelado por hash.** O arquivo `fase2/config/teste_congelado.json` registra o hash SHA-256 de `frases_risco.csv` antes da primeira avaliação. Qualquer modificação nas 60 frases de teste é detectada e reportada pelo harness — impedindo o data leakage clássico de ajustar o conjunto de teste para melhorar a métrica.

- **Pendências de validação clínica (Dra. Fernanda Fassina):**
  - Critério de rótulo e pesos das associações na base de conhecimento
  - Inclusão do padrão angina em crescendo como SCA
  - Peso de edema associado à IC (RELATO 08)
  - IC como sugestão principal do RELATO 08

---

## 8. Engenharia de ML — harness e reprodutibilidade

### 8.1 Testes automatizados (150 testes pytest)

O harness cobre todos os contratos do SDD em arquivos separados por responsabilidade:

| Arquivo de teste | O que verifica |
|---|---|
| `test_base_conhecimento.py` | 10 regras do SDD §3: colunas, IDs únicos, integridade referencial, fontes, paridade de gênero… |
| `test_mapa_conhecimento.py` | Mapa derivado sincronizado com as 5 tabelas |
| `test_extrator_golden.py` | 10/10 relatos com a condição esperada no gabarito |
| `test_comportamento.py` | Negação, gênero, acento, coloquial, atípico |
| `test_analisador_clinico.py` | Pontuação, empate, sugestão única, inconclusivo |
| `test_contrato_dataset.py` | Schema de `frases_risco.csv`, proporções, hash congelado |
| `test_avaliacao.py` | Metas gates: recall ≥ 0,90, acurácia ≥ 0,80 |

**`xfail_strict = true`:** limitações conhecidas são marcadas com `@pytest.mark.xfail` + referência ao SDD §7. Se uma limitação for corrigida e o teste passar, o CI falha — forçando a remoção do marcador e a atualização da documentação.

### 8.2 Reprodutibilidade

- **Seed fixo: 42** em todo código com aleatoriedade (`random_state=42`, `SEED=42`).
- **Splits estratificados** (`stratify=y`) em toda divisão treino/teste.
- **Hash do dataset** no JSON de métricas — qualquer corrida com dataset diferente produz hash diferente, detectável.
- **Hook PostToolUse:** edições em `fase2/knowledge_base/*.csv` disparam automaticamente `test_base_conhecimento.py` e `test_mapa_conhecimento.py` — impedindo que a base quebre silenciosamente.

### 8.3 CI no GitHub Actions

[`.github/workflows/ci-fase2.yml`](.github/workflows/ci-fase2.yml) executa a cada push:
1. Suite completa pytest
2. Verificação de sincronização do mapa derivado
3. Execução dos 3 notebooks com `nbconvert --execute`

### 8.4 Agentes de IA especializados

Quatro agentes foram criados em `.claude/agents/`, adaptados do catálogo [Tech Leads Club agent-skills](https://github.com/tech-leads-club/agent-skills) (CC-BY-4.0):

| Agente | Baseado em | Função |
|---|---|---|
| `/revisor-clinico` | `the-judge` v1.4.0 | Revisa mudanças na KB com evidências do SDD §3 |
| `/devil-advocate` | `the-fool` | Red-team de relatos e KB antes de commitar |
| `/modo-autonomo` | `not-your-babysitter` v1.0.0 | Executa o pipeline completo sem interrupções |
| `/registrar-decisao` | `create-adr` | Lavra CDRs (Clinical Decision Records) para decisões clínicas |

---

## 9. Especificação (SDD) e rastreabilidade

Documento completo: [`.spec/SDD-fase2-nlp-triagem.md`](.spec/SDD-fase2-nlp-triagem.md).

O SDD é a fonte de verdade do comportamento esperado: todo requisito da rubrica tem um ID rastreável (R1–R11), um artefato associado e um teste no harness que o verifica. A relação não é ornamental — o CI falha se qualquer R for violado.

| ID | Requisito | Critério (pts) | Status |
|---|---|---:|---|
| R1 | 10 relatos com sintoma, início e impacto | 2 | ✅ |
| R2 | Mapa KB íntegro e rastreável a fontes | (2) | ✅ |
| R3 | Mapa no formato enunciado | (2) | ✅ 82 linhas |
| R4 | Extrator encontra conceitos esperados | 2 | ✅ 10/10 |
| R5 | Sugestão única por relato | 2 | ✅ |
| R6 | Tratamento de negação | 2 | ✅ |
| R7 | Dataset cumpre contrato | 1 | ✅ 320 frases |
| R8 | Metas atingidas no teste manual | 2 | ✅ recall 0,90 |
| R9 | Notebooks executam sem erro | (2) | ✅ |
| R10 | Vieses medidos e discutidos | 2 | ✅ 6 tipos |
| R11 | README completo, integrantes + RM, link vídeo | 1 | ⚠️ RMs e link pendentes |

---

## 10. Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| `fase2/config/` | `metas_avaliacao.json`, `teste_congelado.json` |
| `fase2/data/` | `relatos_pacientes.txt`, `frases_risco.csv` (+ `_LINHAGEM.md`), `casos_comportamento.csv` |
| `fase2/knowledge_base/` | 5 CSVs normalizados + `mapa_conhecimento.csv` (derivado) + `README.md` |
| `fase2/notebooks/` | `01_extracao_sintomas.ipynb`, `02_classificador_risco.ipynb`, `03_analise_vieses.ipynb` |
| `fase2/reports/` | `metricas_todos.json` (resultado oficial versionado) |
| `fase2/src/` | `extrator_sintomas.py`, `analisador_clinico.py`, `carregador_base.py`, `main.py`, `gerar_mapa_conhecimento.py`, `vieses.py`, `contrato_dataset.py`, `avaliacao.py`, `classificador_regras.py` |
| `fase2/tests/` | Um arquivo por contrato/requisito + `conftest.py` + `golden/` |
| `.claude/agents/` | 4 agentes especializados (revisor-clinico, devil-advocate, modo-autonomo, registrar-decisao) |
| `.spec/` | `SDD-fase2-nlp-triagem.md` + ADRs + especificações da Fase 1 |
| `.github/workflows/` | `ci-fase2.yml` |

---

## 11. Próximos passos

1. **Preencher os RMs e o link do vídeo** no `README.md` e `fase2/README.md` antes da submissão (R11 é o único requisito com item pendente).
2. **Validação clínica com a Dra. Fernanda:** critério de rótulo, pesos das associações, RELATO 08 — formalizar no formato CDR usando `/registrar-decisao`.
3. **Revisão humana do dataset:** a equipe deve escrever um segundo conjunto de teste cego (sem conhecimento dos critérios A1–B3) para validação externa das frases manuais.
4. **Lematização:** a limitação de conjugação verbal (recall 1/5 na dispneia grave com verbos no presente) é o bug mais impactante identificado — a correção natural é adicionar um lematizador PT-BR antes da lookup de expressões.
5. **Recall por sexo com dado real:** cruzar as predições com a distribuição PNS 2013 por sexo para medir o viés de apresentação atípica em escala real.
6. **Fase 3 — modelo preditivo:** usar `CKM_Stage` (Fase 1) como rótulo para treinar um classificador supervisionado nos dados numéricos, integrando o risco calculado na Fase 1 com os sintomas textuais da Fase 2.

---

## 12. Histórico de revisões

| Data | Mudança |
|---|---|
| 2026-10-07 | Documento criado consolidando o estado do projeto ao final da Fase 2: base de conhecimento normalizada, extrator com negação e pontuação explicável (10/10 no gabarito), classificador Naive Bayes (recall 0,900 e acurácia 0,917 no teste congelado), análise de 6 tipos de viés, harness de 150 testes, CI, 4 agentes de IA especializados e SDD com rastreabilidade completa R1–R11. |
