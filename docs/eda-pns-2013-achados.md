# EDA — Achados sobre Valores Ausentes e Outliers (PNS 2013)

| | |
|---|---|
| **Projeto** | CardioIA — Fase 1 (Batimentos de Dados) |
| **Escopo** | Exploração inicial de `data/processed/pns_ckm_rce_2013.csv` em R |
| **Notebook associado** | [`notebooks/exploracao_pns.R`](../notebooks/exploracao_pns.R) (§1-5) + [`notebooks/exploracao_ckm_stage.R`](../notebooks/exploracao_ckm_stage.R) (§6) |
| **Status** | Investigação de outliers concluída (§5) + validação clínica do `CKM_Stage` concluída (§6) |
| **Última revisão** | 2026-09-01 |

---

## 1. Bug de leitura: `read.csv` esconde `NA` como string vazia

**Sintoma:** `sort(colSums(is.na(dados_br)), decreasing = TRUE)` mostrava `0` ausências em todas as colunas de texto (`Diabetes_Diagnosticado`, `Hipertensao_Diagnosticada`, `Colesterol_Alto_Diagnosticado`, `Insuficiencia_Cardiaca`, `Doenca_Coronariana`, `Infarto_Miocardio`, `AVC`, `Sintoma_Dor_Desconforto_Peito`, `Raca_Etnia`) — número que não batia com o log de linhagem do pipeline Python.

**Causa:** o `pandas` grava valor ausente como campo vazio no CSV (nada entre as vírgulas). O `read.csv()` do R, por padrão, só reconhece o texto literal `"NA"` como ausência (`na.strings = "NA"`). Em coluna **numérica**, campo vazio não converte pra número e vira `NA` de qualquer forma — por isso essas colunas estavam corretas. Em coluna de **texto**, campo vazio vira a string `""`, que `is.na()` não pega.

**Confirmação:**
```r
sort(colSums(dados_br == "", na.rm = TRUE), decreasing = TRUE)
```
Bateu exatamente com os números do log de linhagem do Python (ex.: `Infarto_Miocardio` = 8.548, `Diabetes_Diagnosticado` = 1.125).

**Correção — sempre ler este CSV assim:**
```r
dados_br <- read.csv(
  "C:/Users/caroo/OneDrive/Desktop/FIAP/projetos/cardioIA/data/processed/pns_ckm_rce_2013.csv",
  na.strings = c("NA", "")
)
```

---

## 2. Classificação dos valores ausentes (depois da correção acima)

Nem todo `NA` tem a mesma causa — o tratamento certo depende do motivo. Ver também `.spec/SDD-pipeline-pns-ckm.md` §5.1 e §5.3, que documentam a origem desses grupos do lado do pipeline Python.

| Grupo | Colunas | n ausentes | Causa | Tratamento recomendado |
|---|---|---|---|---|
| **A — pergunta condicional (skip pattern)** | `Insuficiencia_Cardiaca`, `Doenca_Coronariana`, `Infarto_Miocardio` | 8.548 cada | Só perguntado a quem respondeu "Sim" à pergunta guarda-chuva Q063 ("algum médico já lhe deu diagnóstico de doença do coração?") | **Recodificar `NA` → `"Nao"`** — a lógica do questionário garante essa resposta (quem nunca teve doença do coração não pode ter tido infarto por causa dela) |
| **B — categoria ambígua excluída deliberadamente** | parte do `NA` de `Diabetes_Diagnosticado` (1.125 no total) e `Hipertensao_Diagnosticada` (426 no total) | 38 / 144 respectivamente | Código "2 = só durante a gravidez" não representa diagnóstico crônico nem sua ausência — o pipeline já mapeia esse código pra `NaN` (não confundir com não-resposta) | Manter como `NA` — não há valor a inferir aqui |
| **C — exame de sangue não coletado / amostra inadequada** | `Creatinina_Serica_mgdL`, `HbA1c_pct`, `Colesterol_Total_mgdL`, `HDL_mgdL`, `LDL_mgdL`, `eGFR_CKD_EPI_2021` | 411–432 (~4,6–4,8%) | Amostra de sangue não processada/inadequada na coleta 2014-2015 | **Decisão adiada pra fase de modelagem** (deixar `NA` pra árvore/XGBoost, ou avaliar imputação por mediana/múltipla) |
| **D — medição antropométrica/PA não realizada** | `Peso_kg`, `Altura_cm`, `Circunferencia_Cintura_cm`, `IMC`, `RCE`, `PA_Sistolica_mmHg`, `PA_Diastolica_mmHg` | 97 (~1,1%) | Pessoa não foi pesada/medida no dia da entrevista | Mesma decisão adiada do Grupo C |
| **E — não-resposta residual** | `Colesterol_Alto_Diagnosticado` (1.390), restante de `Diabetes_Diagnosticado`/`Hipertensao_Diagnosticada` não explicado pelo Grupo B, `AVC` (8), `Raca_Etnia` (2, "Ignorado"), `Regiao` (6) | variável | Recusa/não sabe, ou categoria "Ignorado" | Volume baixo, tratar como ausência genuína |

**Regra de ouro aplicada:** nenhum `NA` é removido ou imputado no CSV "fonte da verdade" — qualquer imputação fica pra uma etapa de modelagem separada e documentada, mesmo princípio já usado no pipeline Python (reportar, não decidir silenciosamente).

---

## 3. Metodologia de detecção de outliers usada

Testamos, em ordem de sofisticação, e adotamos a combinação de **IQR + faixa de plausibilidade clínica**:

| Método | Quando usar | Limitação |
|---|---|---|
| Boxplot/histograma | Primeira inspeção visual | Não quantifica |
| IQR (Tukey): `x < Q1-1,5×IQR` ou `x > Q3+1,5×IQR` | Padrão geral, não assume normalidade | Superestima outliers em variável assimétrica |
| Z-score (`\|z\| > 3`) | Variável ~normal | Sensível — média/desvio-padrão distorcidos pelos próprios outliers |
| Z-score modificado (MAD) | Variável com cauda longa | Mais robusto, menos intuitivo |
| **Faixa de plausibilidade clínica** | Sempre que se sabe o limite biológico | **Prevalece sobre o estatístico** — "raro" ≠ "impossível" |

Função usada (IQR):
```r
detectar_outliers_iqr <- function(x) {
  q1 <- quantile(x, 0.25, na.rm = TRUE)
  q3 <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  x < (q1 - 1.5 * iqr) | x > (q3 + 1.5 * iqr)
}
```

Função de resumo (outlier count + faixa do grupo outlier vs. faixa geral):
```r
resumir_outliers <- function(x) {
  outlier <- detectar_outliers_iqr(x)
  c(
    n_outliers  = sum(outlier, na.rm = TRUE),
    min_outlier = suppressWarnings(min(x[outlier], na.rm = TRUE)),
    max_outlier = suppressWarnings(max(x[outlier], na.rm = TRUE)),
    min_geral   = min(x, na.rm = TRUE),
    max_geral   = max(x, na.rm = TRUE)
  )
}
```

Visualização (boxplot por variável, escalas independentes):
```r
dados_br %>%
  select(all_of(variaveis_numericas)) %>%
  pivot_longer(everything(), names_to = "variavel", values_to = "valor") %>%
  ggplot(aes(x = variavel, y = valor)) +
  geom_boxplot() +
  facet_wrap(~ variavel, scales = "free") +
  theme(axis.text.x = element_blank())
```

---

## 4. Resultado por variável (execução de referência)

| Variável | n_outliers | min_outlier | max_outlier | min_geral | max_geral |
|---|---|---|---|---|---|
| RCE | 59 | 0,796 | 0,948 | 0,329 | 0,948 |
| IMC | 190 | 13,11 | 61,35 | 13,11 | 61,35 |
| PA_Sistolica_mmHg | 304 | 168,5 | 248,5 | 81,5 | 248,5 |
| PA_Diastolica_mmHg | 167 | 44,0 | 137,5 | 44,0 | 137,5 |
| Colesterol_Total_mgdL | 116 | 67 | 433 | 67 | 433 |
| HDL_mgdL | 169 | 6 | 160 | 6 | 160 |
| LDL_mgdL | 98 | 22 | 261 | 22 | 261 |
| **HbA1c_pct** | **593** | 3,58 | 15,96 | 3,58 | 15,96 |
| Creatinina_Serica_mgdL | 201 | 0,20 | 11,86 | 0,20 | 11,86 |
| eGFR_CKD_EPI_2021 | 64 | 3,77 | 171,39 | 3,77 | 171,39 |

**Leitura geral:** na maioria das variáveis, os extremos flagados são clinicamente plausíveis (raros, não impossíveis) — PA sistólica até 248 (crise hipertensiva), colesterol até 433 (hipercolesterolemia familiar), creatinina até 11,86 (insuficiência renal grave). Nenhum caso de valor biologicamente impossível encontrado até agora.

---

## 5. Achados específicos

### 5.1 HbA1c tem ~3x mais outliers que qualquer outra variável — explicado, não é anomalia
593 outliers é desproporcional porque a distribuição é **bimodal**: a maioria da população saudável está bem concentrada perto de 5% (IQR estreito), e qualquer diabético real com HbA1c 7-9% (controle ruim, mas pessoa real) já estoura esse limite estreito. **Lição:** uma variável com muito mais outlier que as outras pode indicar uma subpopulação real (saudável vs. diabético) escondida na mesma coluna, não erro de captura.

### 5.2 eGFR alto (até 171) explicado por creatinina baixa em gente jovem — investigado, não é anomalia
Isolamos as 5 pessoas com `eGFR_CKD_EPI_2021 > 150`:

| ID_Participante | Idade | Sexo | Creatinina_Serica_mgdL | eGFR_CKD_EPI_2021 |
|---|---|---|---|---|
| 653 | 28 | M | 0,32 | 163,04 |
| 1234 | 36 | M | 0,23 | 171,39 |
| 4384 | 26 | F | 0,28 | 152,46 |
| 4912 | 31 | F | 0,20 | 160,27 |
| 4968 | 31 | F | 0,20 | 160,27 |

Todas jovens (26-36 anos) com creatinina baixa (0,20-0,32 mg/dL). Creatinina é subproduto do metabolismo muscular — pessoas jovens e com menos massa muscular (a maioria aqui é mulher) naturalmente produzem menos. Como a fórmula CKD-EPI 2021 é inversamente proporcional à creatinina, isso empurra o eGFR pra cima matematicamente. **Conclusão: não é erro nem hiperfiltração patológica, é consequência esperada da fórmula aplicada a um perfil jovem/baixa massa muscular.**

Nota lateral: `ID_Participante` 4912 e 4968 têm valores idênticos de eGFR (160,27) por terem exatamente a mesma idade, sexo e creatinina — o eGFR é uma fórmula determinística, então entradas idênticas sempre produzem saídas idênticas. Não é bug de duplicação de linha.

### 5.3 HDL mínimo de 6 mg/dL — investigado, inconclusivo
Isolamos `ID_Participante` 2720 (54 anos, M): `Colesterol_Total_mgdL = 170`, `HDL_mgdL = 6`, `LDL_mgdL = 78`.

**Teste 1 — coerência matemática:** `Colesterol_Total` deveria ser sempre maior que `HDL + LDL` somados (a diferença é o VLDL, sempre positivo). Aqui, `170 - (6+78) = 86` — positivo, portanto **matematicamente possível**, não um valor impossível.

**Teste 2 — corroboração clínica:** um HDL tão baixo combinado com esse "excesso" de 86 (que implicaria triglicerídeos estimados de ~430 mg/dL) é um padrão comumente associado a diabetes/síndrome metabólica. Testamos essa hipótese olhando `HbA1c_pct` (4,91% — normal) e `Diabetes_Diagnosticado`/`Colesterol_Alto_Diagnosticado` (ambos "Nao") da mesma pessoa — **a hipótese não se confirmou**.

**Limite encontrado:** `Diabetes_Diagnosticado`/`Colesterol_Alto_Diagnosticado` são autorreferidos ("algum médico já lhe disse que...") — um "Nao" não descarta a condição, só significa que nunca foi diagnosticada. Não há mais nenhuma coluna nesta base (fumo, medicação, IMC isolado) pra desempatar.

**Conclusão: ambíguo.** O valor passa no teste matemático mas não no teste de corroboração clínica, e a base não tem informação suficiente pra decidir com segurança entre "caso raro real" e "erro de captura". Mantido sem alteração no CSV, documentado como caso inconclusivo — não removido nem imputado.

### 5.4 IMC mínimo de 13,11 — investigado, provavelmente real
Isolamos `ID_Participante` 3728 (18 anos, F): `Peso_kg = 37`, `Altura_cm = 168`, `IMC = 13,11`.

**Teste 1 — a conta bate?** `37 / (1,68)² = 13,11` — exatamente igual ao valor salvo na coluna `IMC`. Diferente do caso do HDL, aqui não existe uma terceira variável escondida: o IMC é calculado direto de peso e altura, então esse teste confirma que não há erro de cálculo/gravação.

**Teste 2 — peso e altura são plausíveis isoladamente?** `Altura_cm = 168` é normal. `Peso_kg = 37` é extremo — abaixo da faixa "abaixo do peso" (IMC 18,5-24,9 corresponderia a 52-70 kg nessa altura), na categoria clínica de magreza severa (IMC < 16), compatível com desnutrição grave ou anorexia nervosa em estágio avançado.

**Corroboração demográfica:** 18 anos, mulher, é exatamente o perfil de maior risco pra transtornos alimentares graves — diferente do caso do HDL (onde a corroboração clínica falhou), aqui o perfil demográfico é consistente com o valor extremo.

**Hipótese concorrente não descartável:** troca de dígitos (`37` no lugar de `73`, que daria IMC 25,9 — sobrepeso leve, bem mais comum). Não há outra coluna nesta base pra desempatar entre as duas hipóteses.

**Conclusão: provavelmente real**, não erro de cálculo — mas mantido com a ressalva da possível troca de dígito, sem confirmação de 100%. Valor mantido sem alteração no CSV.

---

## 6. EDA do `CKM_Stage`: validação clínica (não só lógica)

`tests/validar_ckm_stage.py` já provou que `CKM_Stage` é consequência lógica fiel dos classificadores (.spec/especificacao-estagios-ckm.md §6.3). Esta seção verifica se ele também é **clinicamente plausível**, cruzando com idade, sexo, e a concordância entre `Obesidade` (IMC) e `Obesidade_Central` (RCE). Código em [`notebooks/exploracao_ckm_stage.R`](../notebooks/exploracao_ckm_stage.R), rodado sobre `data/processed/pns_ckm_prevent_2013.csv`.

### 6.1 `CKM_Stage` vs. Idade — progressão monotônica, sem inversão

| Estágio | Idade média | Idade mediana | n |
|---|---|---|---|
| 0 | 30,9 | 28,5 | 1.364 |
| 1 | 39,2 | 37 | 2.264 |
| 2 | 49,4 | 49 | 4.929 |
| 4 | 61,2 | 61 | 395 |

Sobe de forma estritamente crescente (31 → 39 → 49 → 61 anos), sem nenhuma inversão entre estágios. Confirma clinicamente o que já tínhamos provado logicamente: a hierarquia se comporta como esperado frente a uma variável totalmente externa à sua própria construção.

### 6.2 `CKM_Stage` vs. Sexo — assimetria esperada

| Sexo | 0 | 1 | 2 | 4 |
|---|---|---|---|---|
| F | 15,7% | 28,5% | 51,2% | 4,6% |
| M | 14,6% | 20,8% | **60,5%** | 4,2% |

Homens concentram mais em Estágio 2 (60,5% vs. 51,2%) e menos em Estágio 1 (20,8% vs. 28,5%) que mulheres — consistente com o padrão epidemiológico conhecido de homens acumularem fatores de risco metabólico/hipertensivo mais cedo, enquanto mulheres tendem a "alcançar" esse perfil depois da menopausa.

### 6.3 Concordância `Obesidade` (IMC) x `Obesidade_Central` (RCE) — achado mais forte da EDA

| Obesidade (IMC) | Obesidade_Central (RCE) | n | % |
|---|---|---|---|
| Nao | Nao | 2.119 | 23,7% |
| **Nao** | **Sim** | **4.794** | **53,6%** |
| Sim | Nao | 16 | 0,2% |
| Sim | Sim | 1.926 | 21,5% |
| NA | NA | 97 | 1,1% |

**Mais da metade da amostra (53,6%) é "peso normal" pelo IMC mas "obesidade central" pela RCE.** Olhando o `CKM_Stage` só desse grupo discordante, contra a população geral:

| Estágio | Grupo discordante (IMC normal, RCE alterada) | População geral |
|---|---|---|
| 0 | **0%** | 15,2% |
| 1 | 35,9% | 25,3% |
| 2 | 59,1% | 54,9% |
| 4 | 5,0% | 4,4% |

**Zero por cento do grupo discordante está em Estágio 0** — ninguém que o IMC classificaria como saudável, mas a RCE marca como risco central, está livre de algum fator de risco cardiometabólico. Essa é evidência direta, obtida da própria base do projeto, de que **a RCE captura risco real que o IMC sozinho deixa passar** — a tese científica que motivou a escolha da RCE como indicador central deste projeto desde o início, agora com número.

## 7. Referências cruzadas

- [`.spec/SDD-pipeline-pns-ckm.md`](../.spec/SDD-pipeline-pns-ckm.md) — dicionário de dados, faixas de plausibilidade originais (§5.5) e origem dos grupos de ausência (§5.1, §5.3)
- [`.spec/especificacao-estagios-ckm.md`](../.spec/especificacao-estagios-ckm.md) — definição do `CKM_Stage` e sua validação de fidelidade (§6.3) e de interpretação (§6.4)
- [`notebooks/exploracao_pns.R`](../notebooks/exploracao_pns.R) — notebook da EDA de valores ausentes e outliers (seções 1-5)
- [`notebooks/exploracao_ckm_stage.R`](../notebooks/exploracao_ckm_stage.R) — notebook da EDA do `CKM_Stage` (seção 6)

## 8. Histórico de revisões

| Data | Mudança |
|---|---|
| 2026-08-31 | Documento criado a partir da sessão de EDA: bug de leitura do `read.csv`, classificação dos valores ausentes em 5 grupos, metodologia de outlier (IQR + plausibilidade clínica), resultado por variável, e investigação de HbA1c/eGFR. HDL=6 e IMC=13,11 seguem como pendências. |
| 2026-08-31 | HDL=6 investigado: passa no teste de coerência matemática (Total > HDL+LDL) mas não se confirma clinicamente (HbA1c normal, sem diagnóstico de diabetes/colesterol alto) — encerrado como **inconclusivo**, valor mantido sem alteração. IMC=13,11 segue como única pendência. |
| 2026-08-31 | IMC=13,11 investigado: cálculo confere exatamente (`Peso_kg/Altura_cm²`), e o perfil demográfico (18 anos, mulher) é consistente com magreza severa/anorexia — encerrado como **provavelmente real**, com ressalva de possível troca de dígitos não descartável. Todas as pendências de outlier fechadas. |
| 2026-09-01 | Seção 6 adicionada: EDA do `CKM_Stage` — idade progride monotonicamente por estágio (31→39→49→61 anos), assimetria por sexo consistente com epidemiologia conhecida, e achado forte de que 53,6% da amostra é discordante entre IMC e RCE, com esse grupo discordante 0% em Estágio 0 (vs. 15,2% da população geral) — evidência de que a RCE captura risco real que o IMC não pega. |
