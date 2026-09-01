# Relatório Técnico — CardioIA, Fase 1: Batimentos de Dados

| | |
|---|---|
| **Projeto** | CardioIA — Diagnóstico e Alerta Precoce da Síndrome Cardiorrenal-Metabólica |
| **Curso** | Inteligência Artificial, FIAP |
| **Supervisão clínica** | Dra. Fernanda Fassina (Cardiologista e Clínica Geral, CRM-SP 169944) |
| **Escopo deste relatório** | Estado do projeto ao final da Fase 1 — dados, governança, especificação e validação do `CKM_Stage` |
| **Última revisão** | 2026-09-01 |

---

## 1. Resumo executivo

O CardioIA é um sistema de suporte à decisão clínica (CDSS) para identificar precocemente pacientes em risco da **Síndrome Cardiorrenal-Metabólica (CKM)** — uma condição que hoje é diagnosticada tarde porque seus três eixos (metabólico, renal, cardiovascular) são avaliados por especialistas diferentes, sem cruzamento sistemático das informações.

Nesta fase, o projeto:

1. Construiu um **pipeline reprodutível** que transforma dados brutos da Pesquisa Nacional de Saúde (PNS 2013, IBGE/Fiocruz) num dataset numérico de 8.952 pessoas com todas as variáveis dos 3 eixos da CKM, validado linha a linha contra a fonte original.
2. Reuniu e documentou **dados textuais** (3 artigos científicos, licenças abertas) e **dados visuais** (120 imagens de ECG, licença aberta), com proveniência completa.
3. Especificou e implementou a **classificação em estágios CKM (0 a 4)** seguindo a diretriz oficial AHA/ACC/ADA/ASN 2026, incluindo o estágio mais difícil (doença cardiovascular subclínica) via um escore de risco validado (PREVENT).
4. Validou essa classificação em duas frentes independentes — **fidelidade lógica** (a classificação é consequência correta das regras) e **plausibilidade clínica** (a classificação se comporta como esperado frente a idade, sexo e um teste de concordância entre indicadores).
5. Documentou, de forma explícita, os limites do que pode e do que não pode ser afirmado a partir desses dados.

O resultado é uma base de dados e uma especificação prontas para a próxima fase (modelagem/ML), com cada decisão de projeto e cada limitação registradas em documentos versionados, não apenas na memória de quem construiu.

## 2. Contexto clínico e motivação

A Síndrome Cardiovascular-Renal-Metabólica (CKM) é uma progressão: **excesso/disfunção de adiposidade → fatores de risco metabólico e renal → doença cardiovascular subclínica → doença cardiovascular clínica**. A American Heart Association formalizou essa progressão em estágios (0 a 4) no *Presidential Advisory* de 2023 e, mais recentemente, na diretriz conjunta **AHA/ACC/ADA/ASN de 2026**, publicada em 9 de junho de 2026.

O problema prático que motiva o CardioIA: um paciente pode ter alterações discretas nos 3 eixos — cintura aumentada, glicada levemente alta, pressão arterial no limite — sem que nenhum médico individual (endocrinologista vendo só a glicada, nefrologista vendo só a função renal, cardiologista vendo só a pressão) enxergue o quadro composto. A Dra. Fernanda Fassina identificou esse cruzamento tardio como a principal causa de diagnóstico tardio de Insuficiência Cardíaca e infarto na prática ambulatorial.

A **RCE (Relação Cintura-Estatura)** é um indicador central do projeto por um motivo específico: evidência recente mostra que ela prediz Insuficiência Cardíaca melhor que o IMC, por capturar gordura visceral — e a EDA deste projeto (seção 8) confirmou isso com número da própria base.

## 3. Arquitetura de dados do projeto

O projeto está organizado em **3 partes** (numérica, textual, visual) e, dentro da parte numérica, em **4 camadas** de processamento:

```
Parte 1 (numérica)              Parte 2 (textual)         Parte 3 (visual)
  Camada 1: dado bruto            3 artigos científicos      120 imagens de ECG
  Camada 2: indicadores           (recorte + PDF             (4 classes,
    calculados (IMC, RCE, eGFR)    original destacado)        CC BY 4.0)
  Camada 3: classificadores
    clínicos (Obesidade,
    Hipertensao_CKM, etc.)
  Camada 4: CKM_Stage
```

Cada camada/parte tem seu próprio script gerador, log de linhagem, e documento de especificação — nada é feito manualmente ou fica sem rastro de como foi gerado.

### 3.1 Por que não uma única base pronta

Antes de escolher as fontes, investigamos 19 bases públicas candidatas (MIMIC-IV, UK Biobank, All of Us, PTB-XL, CODE-15%, EchoNet, ACDC, entre outras) atrás de uma única fonte gratuita, aberta, redistribuível e com números clínicos completos + textos + imagens cardíacas. Nenhuma cumpre tudo simultaneamente: as bases clinicamente mais completas exigem credenciamento e proíbem redistribuição por contrato; as bases livres para redistribuir cobrem só uma fatia do conteúdo clínico. Detalhes em [`.spec/decisao-fontes-de-dados.md`](.spec/decisao-fontes-de-dados.md).

## 4. Parte 1 — Dados Numéricos

### 4.1 Por que PNS 2013, e não NHANES

A primeira versão do projeto usava o NHANES (CDC/EUA). Essa escolha tinha uma limitação de viés relevante: o NHANES representa a população dos Estados Unidos, com perfil nutricional, étnico e de acesso à saúde diferente do brasileiro — justamente a população que o CardioIA pretende atender (SUS). Avaliamos as 3 edições da Pesquisa Nacional de Saúde:

| Edição | Tem exame de sangue/urina? | Veredito |
|---|---|---|
| PNS 2019 (mais recente publicada) | ❌ Não | Sem biomarcadores, não dá pra calcular eGFR nem cobrir os pilares renal/metabólico |
| PNS 2026 (em coleta desde jul/2026) | ✅ Vai ter, pela 1ª vez | Coleta só termina em nov/2026, sem microdado disponível ainda |
| **PNS 2013 + módulo de exames (2014-2015)** | ✅ Sim | **Escolhida** — única com biomarcadores reais publicados hoje |

### 4.2 O pipeline de extração

[`src/build_pns_ckm_dataset.py`](src/build_pns_ckm_dataset.py) baixa o arquivo de exames da Fiocruz/ICICT (questionário + laboratório já cruzados por pessoa, ao contrário do NHANES que exigia fundir 12 arquivos) e produz `data/processed/pns_ckm_rce_2013.csv` — **8.952 pessoas, 27 variáveis**, cobrindo os 3 pilares da CKM. Garantias de fidelidade documentadas em [`.spec/SDD-pipeline-pns-ckm.md`](.spec/SDD-pipeline-pns-ckm.md):

- Cada variável categórica foi conferida linha a linha contra o dicionário oficial da PNS, não assumida por convenção.
- eGFR recalculado com CKD-EPI 2021 (sem coeficiente de raça, padrão clínico atual) a partir da creatinina bruta — não o valor pré-calculado da PNS (fórmula 2009, com raça).
- Distinção explícita entre "pergunta condicional" (ex.: só se pergunta sobre infarto a quem já tem diagnóstico de doença do coração) e dado realmente perdido.

**Validado linha a linha:** [`tests/validar_extracao_pns.py`](tests/validar_extracao_pns.py) recalcula, a partir do Excel bruto, cada coluna do CSV final por 3 caminhos diferentes (cópia direta, mapeamento categórico, derivado recalculado do zero) — **as 8.952 linhas batem exatamente, zero divergência.**

### 4.3 Limitações conhecidas (residuais)

- Sem albuminúria (a PNS não coleta esse marcador renal).
- Sem glicemia de jejum direta (só HbA1c; a "glicose estimada" da PNS é derivada matematicamente do HbA1c, por isso foi excluída por redundância).
- Sem sintoma de dispneia (o NHANES tinha; a PNS não pergunta).
- Dado de 2014-2015 — mais antigo que um ciclo NHANES recente, preço de ser a única PNS com exames publicados.
- Pesos amostrais (`Peso_Amostral`) disponíveis mas não aplicados neste CSV bruto — estatísticas descritivas simples não são diretamente representativas da população brasileira sem esse ajuste.

## 5. Parte 2 — Dados Textuais

Três artigos científicos, em `assets/documentos_cientificos/`, cada um com um recorte `.txt` (citação, licença e data de extração no cabeçalho) e o **PDF original com destaque amarelo** exatamente nos trechos usados no recorte — gerados por [`src/destacar_documentos_cientificos.py`](src/destacar_documentos_cientificos.py):

| Documento | Fonte | Licença |
|---|---|---|
| `diretriz_insuficiencia_cardiaca` | Diretriz Brasileira de IC Crônica e Aguda (SBC/DEIC, Arq Bras Cardiol 2018) | CC BY 4.0 |
| `consenso_sindrome_cardiorrenal` | Síndrome Cardiorrenal Aguda... (Leite et al., Arq Bras Cardiol 2020) | CC BY-NC |
| `ckm_current_urgent_concept` | Cardiovascular-Kidney-Metabolic Syndrome: A Current and Urgent Concept (JBN/SciELO, 2025) | CC BY 4.0 |

Todos os 3 são recortes seletivos (não o texto integral) — o destaque no PDF original existe justamente para deixar claro, sem exigir releitura do artigo inteiro, o que foi de fato usado.

## 6. Parte 3 — Dados Visuais

120 imagens de ECG (`assets/imagens_ecg/`), amostra balanceada (30 por classe) do dataset Mendeley Data *"ECG Images dataset of Cardiac Patients"* (Khan, Hussain & Malik, v2, CC BY 4.0), obtidas via API pública do Mendeley. Classes: `Normal`, `Infarto_Miocardio`, `Historico_Infarto_Miocardio`, `Batimento_Anormal`. Verificado por inspeção visual: as imagens não trazem PII do paciente. Detalhes de amostragem e reprodutibilidade em [`assets/imagens_ecg/LINHAGEM.md`](assets/imagens_ecg/LINHAGEM.md).

## 7. Governança, LGPD e viés

- **Privacidade:** os 3 tipos de dado são de fontes públicas desidentificadas (microdados do IBGE sob a Lei de Acesso à Informação; literatura científica; imagens sem PII confirmado por inspeção). Nenhum dado pessoal identificável em nenhuma das 3 partes.
- **Viés de população:** resolvido para a Parte 1 pela troca NHANES→PNS (§4.1). Viés residual documentado: peso amostral não aplicado, dado de 2014-2015, amostra do módulo de exames menor que a PNS completa.
- **Proveniência cruzada:** as 3 partes vêm de indivíduos diferentes — a combinação é pedagógica (uma competência de governança por tipo de dado), não uma coorte real unificada. Isso está declarado explicitamente no README para evitar a impressão de vínculo real entre o CSV numérico e as imagens de ECG.

## 8. EDA — valores ausentes, outliers e validação clínica

Documentado in extenso em [`docs/eda-pns-2013-achados.md`](docs/eda-pns-2013-achados.md). Achados principais:

- **Bug de leitura corrigido:** `read.csv()` do R esconde `NA` como string vazia em colunas de texto (`na.strings` precisa incluir `""` explicitamente) — sem essa correção, 9 colunas apareciam com 0% de ausência quando na verdade tinham até 95,5%.
- **5 grupos de ausência classificados**, cada um com tratamento próprio — de ausência lógica (pergunta condicional, recodificável) a decisão de imputação adiada pra fase de modelagem.
- **Outliers investigados individualmente, não removidos por padrão:** HbA1c com 3x mais outliers que qualquer outra variável, explicado por distribuição bimodal (subpopulação diabética real, não erro); eGFR alto explicado por creatinina baixa em gente jovem; HDL=6 mg/dL encerrado como inconclusivo (passa no teste matemático, não se confirma clinicamente); IMC=13,11 encerrado como provavelmente real (perfil demográfico consistente com magreza severa).
- **Validação clínica do `CKM_Stage`** (não só lógica): idade média sobe de forma monotônica entre estágios (30,9 → 39,2 → 49,4 → 61,2 anos); assimetria por sexo consistente com epidemiologia conhecida; e o achado mais forte — **53,6% da amostra é "peso normal" pelo IMC mas "obesidade central" pela RCE**, e esse grupo discordante tem **0% em Estágio 0** (vs. 15,2% da população geral) — evidência direta, feita com dado deste projeto, de que a RCE captura risco cardiometabólico real que o IMC deixa passar.

## 9. Especificação e implementação do `CKM_Stage`

Documento completo: [`.spec/especificacao-estagios-ckm.md`](.spec/especificacao-estagios-ckm.md).

### 9.1 Matriz indicador → PNS 2013

Antes de escrever código, mapeamos cada indicador exigido pela diretriz oficial contra o dicionário da PNS, confirmando diretamente na fonte (não por suposição) o que existe, o que é derivável, e o que está genuinamente ausente:

| Eixo | Cobertura |
|---|---|
| Adiposidade | 🟢 Completa (peso, altura, cintura medidos; IMC e RCE derivados) |
| Metabolismo | 🟡 Parcial (HbA1c sim; glicemia de jejum direta não) |
| Perfil lipídico | 🟡 Parcial (colesterol/HDL/LDL sim; triglicerídeos **confirmado ausente** no dicionário) |
| Pressão arterial | 🟢 Completa (medida por aparelho, 3 leituras) |
| Rim | 🟡 Parcial (creatinina/eGFR sim; albuminúria **confirmado ausente**) |
| CVD clínica (estágio 4) | 🟢 Quase completa (falta só fibrilação atrial e doença arterial periférica) |
| CVD subclínica (estágio 3) | 🔴 Nenhum dos 4 indicadores oficiais existe (CAC, NT-proBNP, troponina, ecocardiograma) |

### 9.2 Estágio 3: o buraco resolvido via PREVENT

A ausência total de indicadores de CVD subclínica tornaria o Estágio 3 impossível de existir na base. A própria diretriz aceita um critério equivalente: **risco PREVENT de 10 anos ≥ 20%**. [`src/calcular_prevent.R`](src/calcular_prevent.R) calcula esse escore usando o pacote R `CVrisk` (coeficientes oficiais já validados por terceiros — evitando transcrever à mão um paper pago), após extrair 2 variáveis adicionais da PNS bruta (tabagismo, uso de anti-hipertensivo) que ainda não estavam no pipeline. Resultado: **15 pessoas (0,2%) classificadas em Estágio 3 real**, cobertura do escore em 57,3% da amostra (limitado pela faixa etária validada do PREVENT, 30-79 anos).

### 9.3 Distribuição final

| Estágio | % da amostra | Comparação com estudos publicados (NHANES, EUA) |
|---|---|---|
| 0 | 15,2% | 13,2% |
| 1 | 25,3% | 20,8-25,9% |
| 2 | 54,9% | 49,0-53,1% |
| 3 | 0,2% | 5,0-5,4% |
| 4 | 4,4% | 7,8-9,2% |

Estágios 0-2 muito próximos dos números publicados para os EUA — validação externa da lógica de classificação. Estágio 3 mais baixo (esperado, pela limitação de indicadores) e Estágio 4 mais baixo (diferença ainda não totalmente explicada — hipóteses em aberto na especificação §6.1).

### 9.4 Validação de fidelidade

[`tests/validar_ckm_stage.py`](tests/validar_ckm_stage.py) prova, em vez de assumir, que `CKM_Stage` é consequência lógica fiel dos classificadores: recalcula os 6 classificadores da Camada 3 de forma independente e verifica as regras da hierarquia nos dois sentidos, em todas as 8.952 linhas. Na primeira execução, encontrou 1 divergência — investigada e atribuída a uma perda de precisão de ponto flutuante no round-trip via CSV (não a um erro de lógica), corrigida no método do teste e documentada como cuidado para qualquer reuso futuro do dataset. **Resultado final: todas as linhas passam.**

### 9.5 O que `CKM_Stage` não é

Um ponto de interpretação documentado explicitamente (especificação §6.4): `CKM_Stage` não é uma probabilidade nem um diagnóstico confirmado. É a aplicação direta de um critério clínico oficial a uma medição única, num corte transversal. Três razões concretas: (1) uma medição isolada não equivale ao protocolo diagnóstico completo, que geralmente exige confirmação por segunda medição; (2) a definição de cronicidade do KDIGO exige alteração persistente por ≥3 meses, que uma pesquisa transversal não confirma; (3) os desfechos do Estágio 4 são autorreferidos, sujeitos a viés de memória e sub-diagnóstico. Recomendação de linguagem: "valores compatíveis com o critério de Estágio 2", não "tem CKM Estágio 2".

## 10. Estrutura do repositório

Ver [`README.md`](README.md) para a árvore completa e atualizada. Resumo por função:

| Pasta | Conteúdo |
|---|---|
| `src/` | Pipelines de geração (extração PNS, derivação de estágio, PREVENT, destaque de PDF) |
| `tests/` | Validação de fidelidade (extração e classificação) |
| `notebooks/` | EDA em R |
| `data/processed/` | CSVs finais + logs de linhagem |
| `assets/` | As 3 partes de dado (textual e visual) |
| `.spec/` | Especificações técnicas e decisões de arquitetura |
| `docs/` | Achados de EDA |

## 11. Próximos passos

1. Decidir a estratégia de imputação/tratamento de ausência (Grupos C/D da EDA) para a fase de modelagem.
2. Avaliar se o escore PREVENT deve ganhar uma segunda validação (comparação com literatura brasileira de risco cardiovascular, se disponível).
3. Treinar um classificador supervisionado (ML) usando `CKM_Stage`/os desfechos autorreferidos como rótulo — ainda não iniciado nesta fase; requer decisão explícita sobre algoritmo (árvore vs. modelo sensível a escala) e tratamento do desbalanceamento das classes-alvo (ex.: `AVC` tem ~1,9% de prevalência na amostra).
4. Subir os 3 datasets (numérico, textual, visual) para um link público (Drive/OneDrive), conforme exigido para a entrega — pendente de conta pessoal do responsável pelo projeto.

## 12. Histórico de revisões

| Data | Mudança |
|---|---|
| 2026-09-01 | Documento criado consolidando o estado do projeto ao final da Fase 1: as 3 partes de dado, decisões de governança, pipeline PNS validado, especificação e implementação completa do `CKM_Stage` (incluindo Estágio 3 via PREVENT), validação de fidelidade e clínica, e limitações de interpretação. |
