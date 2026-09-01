library(tidyverse)

# CKM_Stage ja foi validado como logicamente fiel aos classificadores
# (tests/validar_ckm_stage.py) — aqui checamos se ele tambem e clinicamente
# plausivel: estagio deveria subir com idade, ter alguma assimetria por sexo,
# e a RCE deveria capturar risco que o IMC sozinho deixa passar.

dados_ckm <- read.csv(
  "C:/Users/caroo/OneDrive/Desktop/FIAP/projetos/cardioIA/data/processed/pns_ckm_prevent_2013.csv",
  na.strings = c("NA", "")
)

# --- 1. CKM_Stage vs Idade -----------------------------------------------
# Esperado: idade media subindo de 0 -> 1 -> 2 -> 4, sem inversao. Se
# inverter em algum ponto, e sinal de problema na hierarquia do CKM_Stage.

dados_ckm %>%
  group_by(CKM_Stage) %>%
  summarise(idade_media = mean(Idade, na.rm = TRUE),
            idade_mediana = median(Idade, na.rm = TRUE),
            n = n())

dados_ckm %>%
  ggplot(aes(x = factor(CKM_Stage), y = Idade)) +
  geom_boxplot() +
  labs(x = "Estágio CKM", y = "Idade")

# --- 2. CKM_Stage vs Sexo --------------------------------------------------
# Proporcao dentro de cada sexo (nao contagem bruta, ja que o total de
# homens e mulheres na amostra e diferente). Exploratorio — nao ha um
# resultado "certo" aqui, so checar se a assimetria observada faz sentido
# clinicamente (ex.: homens com mais risco cardiovascular mais jovens).

dados_ckm %>%
  filter(!is.na(CKM_Stage)) %>%
  count(Sexo, CKM_Stage) %>%
  group_by(Sexo) %>%
  mutate(pct = round(100 * n / sum(n), 1)) %>%
  select(-n) %>%
  pivot_wider(names_from = CKM_Stage, values_from = pct)

# --- 3. Concordancia Obesidade x Obesidade_Central -------------------------
# A celula que importa: Obesidade=Nao e Obesidade_Central=Sim — gente que o
# IMC classificaria "peso normal" mas a RCE pega como risco central.

dados_ckm %>%
  count(Obesidade, Obesidade_Central) %>%
  mutate(pct = round(100 * n / sum(n), 1))

# Se a RCE estiver capturando risco real (nao so ruido), esse grupo
# discordante deveria ter uma concentracao em Estagio 2 MAIOR que a
# populacao geral (~55%, ver linha 1 do bloco 1 acima).

dados_ckm %>%
  filter(Obesidade == "Nao", Obesidade_Central == "Sim") %>%
  count(CKM_Stage) %>%
  mutate(pct = round(100 * n / sum(n), 1))
