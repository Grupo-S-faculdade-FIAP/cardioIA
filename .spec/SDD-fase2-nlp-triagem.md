# SDD — Fase 2: Extração de Sintomas (NLP) e Triagem de Risco

| | |
|---|---|
| **Projeto** | CardioIA — Fase 2 (Diagnóstico Automatizado — IA no Estetoscópio Digital) |
| **Componentes** | C1 `fase2/src/` (extrator + base de conhecimento) · C2 classificador de risco TF-IDF · C3 análise de vieses |
| **Harness de verificação** | `fase2/tests/` (pytest) + `fase2/src/avaliacao.py` (avaliação e metas) |
| **Metas numéricas** | `fase2/config/metas_avaliacao.json` |
| **Status** | C1 v1.2 (negação, pesos por tipo de relação, sugestão única, paridade de gênero) · C2 e C3 em implementação |
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
| R3 | Mapa também no formato do enunciado (`sintoma_1,sintoma_2,doenca_associada`) | Relatos e mapa (2) | `fase2/knowledge_base/mapa_conhecimento.csv` (derivado) | `test_mapa_conhecimento.py` |
| R4 | Extrator encontra os conceitos esperados nos 10 relatos | Extração funcional (2) | `fase2/src/` | `test_extrator_golden.py` |
| R5 | Extrator sugere **uma** condição principal por relato | Extração funcional (2) | `fase2/src/analisador_clinico.py` | `test_extrator_golden.py`, `test_analisador_clinico.py` |
| R6 | Extrator respeita negação ("não sinto dor no peito") | Extração funcional (2) | `fase2/src/extrator_sintomas.py` | `test_comportamento.py` |
| R7 | Dataset de risco cumpre o contrato da §4 | Dataset simples (1) | `fase2/data/frases_risco.csv` + `frases_risco_LINHAGEM.md` | `test_contrato_dataset.py` |
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
8. `tipo_relacao` pertence ao vocabulário controlado da §3.2 (todo tipo tem peso definido).
9. Cada par (conceito, condição) aparece uma única vez em `associacoes.csv`.
10. **Paridade de gênero:** toda expressão ou gatilho com adjetivo que concorda com o paciente (`cansado`, `tonto`, `pálido`, `sentado`, `deitado`, `parado`, `nervoso`…) tem a forma do outro gênero no mesmo conceito/atributo. Sem isso, a mesma queixa escrita por uma mulher deixa de ser reconhecida.
11. Todo gatilho de negação **dentro** de uma expressão da base inicia uma pseudo-negação conhecida (ex.: "fico **sem ar**"), senão a expressão negaria o sintoma seguinte (§3.1).
12. `mapa_conhecimento.csv` é **derivado** (`python fase2/src/gerar_mapa_conhecimento.py`): fica sincronizado com a base e cobre todas as expressões.

### 3.1 Negação (C1 v1.2)

Versão simplificada do NegEx (Chapman et al., 2001) em `extrator_sintomas.py`:

- **Gatilhos:** `não, nem, sem, nunca, jamais, nenhum, nenhuma`. Um gatilho nega a expressão que começa **até 3 palavras** depois dele ("não sinto mais aquela dor no peito").
- **Gatilho imediato:** `quase` nega só a palavra seguinte — "quase desmaiei" é pré-síncope, não síncope.
- **Fim do alcance:** pontuação (`. , ; : ! ? ( )`) e conjunções `mas, porém, contudo, entretanto, todavia, porque, pois, exceto, embora, só, apenas, somente`. "Não sinto dor no peito, só cansaço" → cansaço continua afirmado.
- **Pseudo-negações** (começam com gatilho, mas não negam o que vem depois): "sem ar", "sem querer", "não consigo", "não aguento", "não melhorou", "não só"… Se a locução invade a própria expressão, a negação vale: em "não melhora quando descanso", o atributo *melhora com repouso* (A006) é negado e *não melhora com repouso* (A007) é afirmado.
- **Expressão contida em outra negada herda a negação:** "não acordo de madrugada com falta de ar" nega a DPN **e** a dispneia.
- Conceito só é negado se **todas** as menções estiverem negadas. Negados não pontuam e são exibidos à parte ("sintomas negados pelo paciente").

### 3.2 Pontuação e sugestão (C1 v1.2)

`pontuação(condição) = Σ peso(tipo_relacao) das evidências + 1 × nº de atributos de contexto relevantes presentes`

| `tipo_relacao` | Peso | Exemplo |
|---|---|---|
| manifestação principal | 3 | dor torácica → IAM/SCA, Angina |
| sintoma típico | 2 | dispneia, ortopneia, fadiga → IC |
| manifestação contextual | 2 | edema, oligúria → Congestão / contexto cardiorrenal |
| sintoma menos típico | 1 | tosse noturna, noctúria, edema → IC |
| sintoma associado | 1 | sudorese, náusea → IAM/SCA |
| manifestação compartilhada | 1 | dispneia → Congestão / contexto cardiorrenal |

- Ordenação determinística: pontuação decrescente, depois nome da condição.
- **Sugestão principal** = condição de maior pontuação. **Empate no topo não é desfeito às cegas**: a sugestão fica vazia ("inconclusivo") e as empatadas são exibidas. Os 10 relatos não podem empatar (golden).
- A pontuação é explicativa (ordena hipóteses), **não é probabilidade** nem diagnóstico.

## 4. Contrato do dataset de risco (C2)

**Origem dos dados (reprodutível):**

```
fase2/data/frases_manuais.csv  ──┐   (escritas à mão, uma a uma; contêm TODO o teste)
knowledge_base/ (expressões)   ──┼─► python fase2/src/gerar_frases_risco.py ──► fase2/data/frases_risco.csv
seed 42                        ──┘   (templates só no treino)
```

`frases_risco.csv` é **derivado** (como o mapa da §3): um teste garante que está sincronizado com as fontes. Verificado por `fase2/src/contrato_dataset.py`.

| Coluna | Valores | Observação |
|---|---|---|
| `frase` | texto não vazio | relato curto, PT-BR (1ª pessoa ou acompanhante) |
| `situacao` | `alto risco` \| `baixo risco` | nome exigido pelo enunciado |
| `origem` | `manual` \| `template` | `template` = gerada a partir da base de conhecimento |
| `particao` | `treino` \| `teste` | definida no arquivo, não sorteada no notebook |
| `criterio` | `A1`–`A4` \| `B1`–`B3` | qual regra da §4.1 justifica o rótulo — permite medir recall por tipo de alarme |

Regras:
- **Teste só com frases manuais.** Frases de template reproduzem as regras de rotulagem; avaliar nelas infla a métrica (circularidade).
- **Teste congelado:** o SHA-256 das linhas de teste fica em `fase2/config/teste_congelado.json`. Qualquer mudança quebra o harness e exige atualizar o hash conscientemente, com aprovação da equipe e registro na linhagem (CLAUDE.md §2).
- **Sem duplicata** após normalização em todo o arquivo (impede vazamento treino → teste).
- Tamanho mínimo: 200 frases; teste com ≥ 40 frases.
- Cada classe com ≥ 35% no arquivo inteiro e no teste.
- **Templates concordam com as regras:** todo template recebe, do classificador por regras (`classificador_regras.py`), o mesmo rótulo que o gerador atribuiu — garante que o rótulo segue a §4.1.
- O teste **nunca** é usado para treinar, escolher hiperparâmetro ou escolher modelo — isso é feito por validação cruzada no treino.
- Acompanha `fase2/data/frases_risco_LINHAGEM.md`: como foi gerado, por quem, critério de rótulo, contagens, limitações.

### 4.1 Critério de rótulo (proposta — pendente de validação clínica pela Dra. Fernanda Fassina)

`alto risco` = presença de **sinal de alarme** que, numa triagem, pede atendimento prioritário:

| Código | Sinal de alarme | IDs na base |
|---|---|---|
| A1 | Dor/desconforto torácico **com** qualquer um: em repouso, não melhora com repouso, início súbito, duração > 20 min, irradiação, sudorese, náusea/vômito, **falta de ar**, tontura/síncope, padrão em piora (crescendo) | S013 + (A005, A007, A009, A011–A018, A021–A023, S001, S014–S018) |
| A2 | Síncope (perda de consciência) | S018 |
| A3 | Falta de ar em repouso, súbita, ou que desperta do sono | S001 + (A005, A009) · S003 |
| A4 | Equivalente anginoso / apresentação atípica: sudorese + náusea, ou cansaço súbito intenso com mal-estar, mesmo sem dor no peito | S014 + S015 · S004 + A009 |

> Falta de ar acompanhando dor torácica entrou em A1 porque é o exemplo de `alto risco` do próprio enunciado ("sinto dor no peito e falta de ar").

`baixo risco` = prioridade menor na fila — **não significa ausência de doença**:

| Código | Situação |
|---|---|
| B1 | Sintoma cardiopulmonar leve e estável há semanas/meses, sem sinal de alarme (inclui angina estável: dor ao esforço que melhora com repouso) |
| B2 | Queixa não cardíaca (musculoesquelética, gastrointestinal, respiratória alta...) |
| B3 | Sintoma de alarme explicitamente negado ("não sinto dor no peito"), com no máximo queixa leve |

**Linha de base por regras:** `fase2/src/classificador_regras.py` aplica A1–A4 sobre a saída do extrator da Parte 1 (com negação). É explicável (devolve o motivo) e serve de comparação para o modelo de ML.

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

## 7. Limitações conhecidas

Limitações com teste viram `xfail(strict=True)`: quando forem corrigidas, o teste passa a falhar e obriga a remover o `xfail` e atualizar esta seção.

**Resolvidas na v1.2** (eram `xfail` na v1.1):

| Limitação v1.1 | Correção v1.2 |
|---|---|
| Sem tratamento de negação (R6) | NegEx simplificado (§3.1) |
| Empate IAM × Angina no RELATO 07 | Padrão em crescendo (A011, A021–A023) passou a ser contexto de **IAM/SCA** (AS013): angina que piora, aparece com esforço menor ou em repouso é angina instável — fontes F002/F003 |
| Empate triplo no RELATO 08 | Pesos por `tipo_relacao` (§3.2) + edema periférico associado à IC (AS029, F001). Resultado: **IC** principal, *Congestão / contexto cardiorrenal* como 2ª hipótese — coerente com a regra da base de que edema/oligúria não diagnosticam síndrome cardiorrenal isoladamente. **Pendente de validação clínica (Dra. Fernanda).** |
| Pontuação +1 para qualquer relação | Pesos por `tipo_relacao` (§3.2) |
| Condição `Insuficiência Cardíaca / contexto cardiorrenal` duplicando IC | AS012 renomeada para `Insuficiência Cardíaca` / `sintoma menos típico` (oligúria é sintoma menos típico de IC na F001) |
| Gatilhos só no masculino ("estava sentado", "mesmo estando parado", "me deixando mais cansado") | Formas femininas adicionadas + contrato de paridade de gênero (§3, regra 10) |

**Em aberto** (documentadas; as marcadas com 🧪 têm `xfail` estrito):

- 🧪 **Dupla negação:** "não consigo fazer nada sem falta de ar" é lido como dispneia negada.
- Negação posposta ("dor no peito eu não tenho") e escopo longo (> 3 palavras) não são tratados.
- Incerteza ("acho que é falta de ar") é tratada como afirmação — escolha conservadora para triagem.
- Não distingue sintoma passado de atual ("tive dor no peito há 5 anos").
- **Conjugação verbal:** a base casa só as formas cadastradas — "acordei" não casa com "acordo", "fiquei sem ar" não casa com "fico sem ar". Recall das regras na dispneia grave do teste: 1/5 (notebook 03 §8). Melhoria natural: lematização.
- Atributo ligado a menção negada continua valendo quando fora da janela ("não tenho dor no peito em repouso, mas…" ainda extrai *repouso*).
- Vocabulário de livro: expressões coloquiais fora da base ("agonia no peito", "apaguei", "sem fôlego") não são reconhecidas — medido em C3 (§6), não "decorado" na base.
- Pesos são heurísticos e precisam de validação clínica.

## 8. Como reproduzir

```bash
pip install -r fase2/requirements.txt
pytest fase2                                        # harness completo
python fase2/src/main.py                            # C1 nos 10 relatos
python fase2/src/main.py --texto "Não sinto dor no peito, mas fico sem ar quando me deito"
python fase2/src/gerar_mapa_conhecimento.py         # regenera o mapa achatado após editar a base
python fase2/src/avaliacao.py --modelo todos        # C2 (requer frases_risco.csv)
```
