# CardioIA — Fase 2: Diagnóstico Automatizado (IA no Estetoscópio Digital)

> ⚠️ **AVISO CLÍNICO:** Este sistema é um protótipo acadêmico e **NÃO** substitui avaliação médica.
> Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).

🎥 **Vídeo de demonstração (YouTube, não listado):** [https://youtu.be/dAxV0-LsrXk](https://youtu.be/dAxV0-LsrXk)

## Integrantes

| Nome completo | RM |
|---|---|
| Caroline de Castro Corrêa | RM567255 |
| Enzo França Sader | RM566928 |
| Lucas Hideki Oliveira Koyama | RM566925 |
| Rodrigo Dias Figueiroa | RM567800 |
| Tiago Lindgren Curi | RM567016 |

---

## Resumo

| Parte | O que foi feito | Resultado |
|---|---|---|
| **1 — Extração de sintomas** | 10 relatos simulados, base de conhecimento com fontes científicas e extrator em Python com negação e pontuação explicável | **10/10** relatos com a sugestão esperada; nenhum empate |
| **2 — Classificador de risco** | 320 frases rotuladas por critério clínico, TF-IDF e 3 modelos do scikit-learn, avaliados num teste congelado | Naive Bayes: **acurácia 0,917** e **recall de alto risco 0,900** no teste |
| **Vieses** | Negação, gênero, acento, linguagem coloquial, apresentações atípicas e dado real da PNS 2013 | 6 vieses medidos e documentados, com a mitigação de cada um |

## Onde está cada entregável

| Critério do enunciado | Pts | Arquivo |
|---|---:|---|
| `.txt` com 10 frases de sintomas | 2 | [`data/relatos_pacientes.txt`](data/relatos_pacientes.txt) |
| Mapa de conhecimento em `.csv` (`Sintoma 1 \| Sintoma 2 \| Doença`) | (2) | [`knowledge_base/mapa_conhecimento.csv`](knowledge_base/mapa_conhecimento.csv) — 82 linhas, derivado da [base normalizada](knowledge_base/) |
| Código que lê as frases, identifica sintomas e sugere diagnóstico | 2 | [`src/main.py`](src/main.py) + [`notebooks/01_extracao_sintomas.ipynb`](notebooks/01_extracao_sintomas.ipynb) |
| `.csv` com frases e rótulos (`frase,situacao`) | 1 | [`data/frases_risco.csv`](data/frases_risco.csv) + [linhagem](data/frases_risco_LINHAGEM.md) |
| `.ipynb` com TF-IDF, classificação e avaliação | 2 | [`notebooks/02_classificador_risco.ipynb`](notebooks/02_classificador_risco.ipynb) |
| Distorções e padrões nos resultados | (2) | [`notebooks/03_analise_vieses.ipynb`](notebooks/03_analise_vieses.ipynb) |
| Documentação, repositório público, README | 1 | este arquivo + [SDD](../.spec/SDD-fase2-nlp-triagem.md) |
| Vídeo de até 4 min no YouTube (não listado) | 2 | link no topo |

## Como executar

```bash
pip install -r fase2/requirements.txt

# Parte 1 — extrator nos 10 relatos (ou em um texto livre)
python fase2/src/main.py
python fase2/src/main.py --texto "Não sinto dor no peito, mas fico sem ar quando me deito"

# Parte 2 — treina, escolhe o modelo por validação cruzada e avalia no teste congelado
python fase2/src/avaliacao.py --modelo todos

# Notebooks (já estão executados no repositório, com as saídas)
jupyter notebook fase2/notebooks/

# Harness completo: contratos, gabarito, comportamento e metas
cd fase2 && python -m pytest
```

---

## Parte 1 — Extração de sintomas e sugestão de diagnóstico

```
relato ──► normalização (minúsculas, sem acento)
       ──► expressões do paciente → sintomas    ("fico sem ar" → Dispneia)
       ──► gatilhos de contexto  → atributos   ("vai para o braço" → irradiação)
       ──► negação (NegEx simplificado)        ("não sinto dor no peito" não conta)
       ──► associações da base (sintoma → condição, com tipo de relação e fonte)
       ──► pontuação explicativa ──► sugestão principal (ou "inconclusivo" se empatar)
```

**Base de conhecimento** ([`knowledge_base/`](knowledge_base/)). São 5 tabelas ligadas por IDs:

| Tabela | Conteúdo | Linhas |
|---|---|---:|
| conceitos | sintomas clínicos | 21 |
| expressões | jeitos de o paciente dizer cada sintoma | 99 |
| atributos | contexto: esforço, repouso, irradiação, duração… | 23 |
| associações | sintoma → condição, cada uma com fonte | 29 |
| fontes | diretrizes SBC, Ministério da Saúde, AHA e revisões | 7 |

A base separa **como o paciente fala** do **conceito clínico** e evita regras simplistas ("falta de ar = insuficiência cardíaca"). O `mapa_conhecimento.csv` é a visão achatada no formato do enunciado, gerada por script e conferida por teste.

**Pontuação explicável.** Cada evidência soma o peso do seu tipo de relação, e cada contexto relevante soma 1:

| Tipo de relação | Peso |
|---|---:|
| manifestação principal | 3 |
| sintoma típico / manifestação contextual | 2 |
| demais tipos | 1 |

A pontuação **ordena hipóteses e não é probabilidade**. Trecho da saída de `main.py` para o RELATO 04 (dor no peito súbita em repouso, irradiação para o braço, suor frio e mais de 20 minutos):

```
1. IAM / Síndrome Coronariana Aguda — 11 pontos
   Evidências: Dor/desconforto torácico [manifestação principal, +3]; Sudorese [sintoma associado, +1]; Náusea [sintoma associado, +1]
   Contextos relevantes: A005, A007, A009, A012, A013, A019 (+6)
   Fontes: F002, F003
2. Angina / Doença Coronariana — 5 pontos
   ...
>>> SUGESTÃO PRINCIPAL: IAM / Síndrome Coronariana Aguda
```

| Relato | Quadro | Sugestão principal (pontos) | 2ª hipótese (pontos) |
|---|---|---|---|
| 01 | falta de ar ao esforço, cansaço | Insuficiência Cardíaca (7) | Angina (3) |
| 02 | falta de ar ao deitar (ortopneia) | Insuficiência Cardíaca (7) | empate em 1 ponto |
| 03 | acorda sem ar de madrugada (DPN) | Insuficiência Cardíaca (5) | empate em 1 ponto |
| 04 | dor súbita, irradiação, suor frio, > 20 min | IAM / SCA (11) | Angina (5) |
| 05 | desconforto no peito, tontura, palidez | IAM / SCA (5) | Angina (4) |
| 06 | dor ao esforço que melhora com repouso | Angina (6) | IAM / SCA (4) |
| 07 | angina em crescendo, já em repouso | IAM / SCA (8) | Angina (5) |
| 08 | edema, oligúria, falta de ar, cansaço | Insuficiência Cardíaca (7) | Congestão / contexto cardiorrenal (5) |
| 09 | ganho de peso, noctúria, tosse noturna | Insuficiência Cardíaca (6) | Angina (1) |
| 10 | perda de apetite e de peso, cansaço | Insuficiência Cardíaca (5) | Angina (1) |

## Parte 2 — Classificador de risco (TF-IDF)

**Dataset** ([`data/frases_risco.csv`](data/frases_risco.csv)): 320 frases, 160 de alto risco e 160 de baixo risco.

- **Manuais (140):** escritas uma a uma, com vozes feminina e masculina, linguagem coloquial, relatos de acompanhante e apresentações atípicas.
- **Templates (180):** gerados a partir da base da Parte 1, com seed 42, e usados **só no treino**.
- **Teste:** 60 frases manuais, **congelado por hash antes da primeira avaliação**.
- **Critério de rótulo:** cada frase traz o critério clínico que justifica o rótulo:
  - alto risco: A1 = dor torácica com sinal de alarme, A2 = síncope, A3 = dispneia grave, A4 = equivalente atípico;
  - baixo risco: B1 = sintoma leve e estável, B2 = queixa não cardíaca, B3 = alarme negado.

**Método:**

- **Vetorização:** TF-IDF com unigramas e bigramas.
- **Modelos comparados:** Regressão Logística, Árvore de Decisão e Naive Bayes.
- **Escolha do modelo:** **só por validação cruzada no treino**, pelo maior recall de alto risco. Em triagem, o erro caro é mandar um paciente grave para o fim da fila.

| Sistema | Acurácia (teste) | Recall alto risco | Precisão alto risco |
|---|---:|---:|---:|
| **Naive Bayes (oficial)** | **0,917** | **0,900** | **0,931** |
| Regras da Parte 1 (linha de base) | 0,717 | 0,433 | 1,000 |
| Meta (SDD) | ≥ 0,80 | ≥ 0,90 | — |

O recall ficou **exatamente na meta**: 3 falsos negativos em 30. No teste, a regressão logística teria ido melhor (recall de 0,967). Ela empatou com o Naive Bayes na validação cruzada, e trocar de modelo depois de ver o teste invalidaria a avaliação. Os erros estão explicados termo a termo no notebook 02.

## Vieses encontrados

| Viés | Evidência | Mitigação |
|---|---|---|
| Vocabulário de livro (regras) | Recall de 0,43 no teste; "apaguei", "agonia no peito" e "suando frio" não são reconhecidos | ML treinado com frases variadas; regras usadas como rede de segurança |
| Negação (ML) | "**Não** sinto aperto no peito que vai para o braço" ainda sai com P(alto) = 0,86 | O extrator trata negação; a combinação ML + regras melhora o recall já na validação cruzada (0,977) |
| Pistas espúrias dos templates | "Comecei a sentir… agora" transforma uma dor de cabeça leve em alto risco | Documentado; próxima rodada varia os moldes |
| Gênero gramatical | A base só tinha "estava sentad**o**", "mesmo estando parad**o**"… | Contrato de paridade de gênero e teste contrafactual: 0 inversões |
| Conjugação verbal | "acordei" não casa com "acordo"; regras acertam 1 de 5 casos de dispneia grave | Documentado; lematização na próxima fase |
| **Apresentação atípica (PNS 2013)** | Entre quem já teve infarto, 17% das mulheres relatam dor no peito, contra 26% dos homens. O sintoma discrimina ~3× nas mulheres e ~8× nos homens | Critério A4 (atípico) e frases atípicas no dataset; pendente: recall por sexo com dados reais |

## Engenharia de ML (harness)

- **SDD** ([`.spec/SDD-fase2-nlp-triagem.md`](../.spec/SDD-fase2-nlp-triagem.md)): requisitos ligados à rubrica, contratos de dados, critério de rótulo, metas e limitações.
- **150 testes automatizados** (`pytest`), cobrindo:
  - contrato da base: integridade referencial, paridade de gênero, pseudo-negações;
  - gabarito dos 10 relatos e testes de negação;
  - contrato do dataset, conjunto de teste congelado e concordância dos templates com o critério;
  - metas do classificador.
- **Limitações conhecidas como `xfail` estrito:** quando uma for corrigida, o teste obriga a atualizar a documentação.
- **Hook do Claude Code:** valida a base de conhecimento a cada edição.
- **CI no GitHub Actions** ([`.github/workflows/ci-fase2.yml`](../.github/workflows/ci-fase2.yml)): roda o harness, verifica se o mapa derivado está atualizado e executa os 3 notebooks.

## Estrutura

```text
fase2/
├── config/          metas_avaliacao.json · teste_congelado.json
├── data/            relatos_pacientes.txt · frases_manuais.csv · frases_risco.csv (+ LINHAGEM) · casos_comportamento.csv
├── knowledge_base/  conceitos · expressoes · atributos · associacoes · fontes · mapa_conhecimento.csv (derivado)
├── notebooks/       01_extracao_sintomas · 02_classificador_risco · 03_analise_vieses
├── reports/         metricas_todos.json (resultado oficial da avaliação)
├── src/             extrator_sintomas · analisador_clinico · main · gerar_mapa_conhecimento ·
│                    classificador_regras · gerar_frases_risco · contrato_dataset · avaliacao · vieses
└── tests/           um arquivo por contrato/requisito do SDD + golden/
```

## Limitações e pendências

- **Validação clínica pendente (Dra. Fernanda Fassina):**
  - critério de rótulo e pesos;
  - inclusão do padrão em crescendo como SCA;
  - edema associado à IC;
  - IC como sugestão principal do RELATO 08.
- **Autoria do dataset:** as frases manuais foram redigidas com auxílio de IA generativa (Claude) e ainda precisam de revisão humana. O ideal é a equipe escrever um segundo teste cego.
- Dados **100% sintéticos**: nenhum dado real de paciente. A única base real usada é a PNS 2013 da Fase 1, que é pública e desidentificada.
- Limitações técnicas detalhadas no SDD, §7.

## Créditos

- Base de conhecimento, relatos e extrator v1.1: Enzo França Sader.
- Harness, extrator v1.2, dataset de risco, classificador e análise de vieses: equipe, com auxílio de IA generativa (Claude Code).
