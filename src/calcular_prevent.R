# Calcula o risco PREVENT (10 anos, AHA) e uma versao do CKM_Stage que
# incorpora o Estagio 3 oficial via "risco PREVENT >= 20%" (um dos criterios
# aceitos pela diretriz AHA/ACC/ADA/ASN 2026 quando nao ha exame subclinico
# direto — ver .spec/especificacao-estagios-ckm.md, secoes 5 e 8).
#
# Por que em R, separado do pipeline Python: o pacote CVrisk (que implementa
# a formula PREVENT com os coeficientes oficiais, validados por terceiros)
# so existe em R. O restante do pipeline (extracao + Camadas 2-4 do
# CKM_Stage) continua em Python, ja testado — nao reescrito aqui.
#
# Extrai 2 colunas que ainda nao estavam no CSV (tabagismo: P050; uso de
# anti-hipertensivo: Q006), direto do Excel bruto da PNS, alinhando por
# posicao de linha (mesma lógica ja validada em tests/validar_extracao_pns.py
# do lado Python).
#
# Uso: Rscript src/calcular_prevent.R

library(readxl)
library(dplyr)
library(CVrisk)

repo_root <- "C:/Users/caroo/OneDrive/Desktop/FIAP/projetos/cardioIA"
caminho_bruto <- file.path(repo_root, "data/raw/pns_2013_exames/EXAMES-PNS-2013-FINAL_05052023.xlsx")
caminho_estagios <- file.path(repo_root, "data/processed/pns_ckm_estagios_2013.csv")
caminho_saida <- file.path(repo_root, "data/processed/pns_ckm_prevent_2013.csv")
caminho_log <- file.path(repo_root, "data/processed/pns_ckm_prevent_2013_LINHAGEM.md")

linhas_log <- c()
log <- function(msg) {
  cat(msg, "\n")
  linhas_log <<- c(linhas_log, msg)
}

log(sprintf("Lendo bruto (P050 tabagismo, Q006 uso de anti-hipertensivo): %s", caminho_bruto))
bruto <- read_excel(caminho_bruto) %>%
  select(P050, Q006) %>%
  mutate(P050 = as.character(P050), Q006 = as.character(Q006))

log(sprintf("Lendo dataset com estagios ja calculados: %s", caminho_estagios))
dados <- read.csv(caminho_estagios, na.strings = c("NA", ""))

if (nrow(bruto) != nrow(dados)) {
  stop(sprintf(
    "FALHA CRITICA: bruto tem %d linhas, tratado tem %d — alinhamento por posicao nao e seguro",
    nrow(bruto), nrow(dados)
  ))
}
log(sprintf("%d linhas de cada lado, alinhadas por posicao", nrow(dados)))

dados$Fumante_Atual <- case_when(
  bruto$P050 %in% c("1", "2") ~ "Sim",
  bruto$P050 == "3" ~ "Nao",
  TRUE ~ NA_character_
)
dados$Uso_Anti_Hipertensivo <- case_when(
  bruto$Q006 == "1" ~ "Sim",
  bruto$Q006 == "2" ~ "Nao",
  TRUE ~ NA_character_
)
# Q006 (uso de anti-hipertensivo) so e perguntado a quem respondeu Sim ao
# diagnostico de hipertensao (Q002) — mesma ausencia logica (skip pattern) ja
# documentada para Insuficiencia_Cardiaca/Doenca_Coronariana/Infarto_Miocardio.
# Quem nao tem hipertensao diagnosticada nao usa anti-hipertensivo, por definicao.
n_recodificado <- sum(is.na(dados$Uso_Anti_Hipertensivo) & dados$Hipertensao_Diagnosticada != "Sim", na.rm = TRUE)
dados$Uso_Anti_Hipertensivo[is.na(dados$Uso_Anti_Hipertensivo) & dados$Hipertensao_Diagnosticada != "Sim"] <- "Nao"
log(sprintf("Uso_Anti_Hipertensivo: %d NA recodificados para 'Nao' (ausencia logica — sem diagnostico de hipertensao)", n_recodificado))

log(sprintf("Fumante_Atual: %d Sim, %d Nao, %d NA", sum(dados$Fumante_Atual == "Sim", na.rm = TRUE), sum(dados$Fumante_Atual == "Nao", na.rm = TRUE), sum(is.na(dados$Fumante_Atual))))
log(sprintf("Uso_Anti_Hipertensivo: %d Sim, %d Nao, %d NA", sum(dados$Uso_Anti_Hipertensivo == "Sim", na.rm = TRUE), sum(dados$Uso_Anti_Hipertensivo == "Nao", na.rm = TRUE), sum(is.na(dados$Uso_Anti_Hipertensivo))))

# Traducao pros tipos que o CVrisk::ascvd_10y_prevent espera
dados$Sexo_CVrisk <- case_when(dados$Sexo == "M" ~ "male", dados$Sexo == "F" ~ "female", TRUE ~ NA_character_)
dados$Diabetes_bin <- case_when(dados$Diabetes_Diagnosticado == "Sim" ~ 1, dados$Diabetes_Diagnosticado == "Nao" ~ 0, TRUE ~ NA_real_)
dados$Fumante_bin <- case_when(dados$Fumante_Atual == "Sim" ~ 1, dados$Fumante_Atual == "Nao" ~ 0, TRUE ~ NA_real_)
dados$BP_Med_bin <- case_when(dados$Uso_Anti_Hipertensivo == "Sim" ~ 1, dados$Uso_Anti_Hipertensivo == "Nao" ~ 0, TRUE ~ NA_real_)
# PNS nao pergunta uso de estatina — assumido 0 (nao usa) para todos, ver
# .spec/especificacao-estagios-ckm.md secao 8. Isso tende a SUBESTIMAR o
# risco de quem realmente usa estatina (a formula presume perfil lipidico
# sem tratamento), entao o risco calculado aqui e um teto, nao uma media.
dados$Statin_bin <- 0

calcular_prevent_seguro <- function(sexo, idade, pas, bp_med, colesterol, hdl, statin, diabetes, fumante, egfr, imc) {
  entradas <- c(pas, bp_med, colesterol, hdl, statin, diabetes, fumante, egfr, imc)
  if (is.na(sexo) || any(is.na(entradas))) return(NA_real_)
  if (is.na(idade) || idade < 30 || idade > 79) return(NA_real_)  # PREVENT so validado 30-79 anos
  tryCatch(
    ascvd_10y_prevent(gender = sexo, age = idade, sbp = pas, bp_med = bp_med,
                       totchol = colesterol, hdl = hdl, statin = statin,
                       diabetes = diabetes, smoker = fumante, egfr = egfr, bmi = imc),
    error = function(e) NA_real_
  )
}

log("Calculando risco PREVENT (10 anos) — so para 30-79 anos com as 11 variaveis completas...")
dados$Risco_PREVENT_10anos_pct <- mapply(
  calcular_prevent_seguro,
  dados$Sexo_CVrisk, dados$Idade, dados$PA_Sistolica_mmHg, dados$BP_Med_bin,
  dados$Colesterol_Total_mgdL, dados$HDL_mgdL, dados$Statin_bin,
  dados$Diabetes_bin, dados$Fumante_bin, dados$eGFR_CKD_EPI_2021, dados$IMC
)
log(sprintf(
  "Risco PREVENT calculado para %d de %d pessoas (%.1f%%) — o resto ficou fora da faixa 30-79 anos ou tinha alguma variavel de entrada ausente",
  sum(!is.na(dados$Risco_PREVENT_10anos_pct)), nrow(dados), 100 * mean(!is.na(dados$Risco_PREVENT_10anos_pct))
))

# Estagio 3 oficial: risco PREVENT >= 20% e um dos criterios aceitos pela
# diretriz quando nao ha exame subclinico direto (CAC/NT-proBNP/troponina/eco).
dados$CKM_Stage_Com_PREVENT <- case_when(
  dados$CKM_Stage == 4 ~ 4,
  !is.na(dados$Risco_PREVENT_10anos_pct) & dados$Risco_PREVENT_10anos_pct >= 20 ~ 3,
  TRUE ~ dados$CKM_Stage
)

log("\nDistribuicao de CKM_Stage_Com_PREVENT (agora com Estagio 3 real, via criterio PREVENT):")
tabela_estagios <- table(dados$CKM_Stage_Com_PREVENT, useNA = "ifany")
for (i in seq_along(tabela_estagios)) {
  nome <- names(tabela_estagios)[i]
  if (is.na(nome)) nome <- "NA"
  log(sprintf("  %s: %d (%.1f%%)", nome, tabela_estagios[[i]], 100 * tabela_estagios[[i]] / nrow(dados)))
}

# Colunas *_bin e Sexo_CVrisk sao andaimes internos so pra alimentar o CVrisk —
# redundantes com Sexo/Diabetes_Diagnosticado/Fumante_Atual/Uso_Anti_Hipertensivo
# ja presentes no CSV, entao nao vao pro arquivo final.
dados_finais <- dados %>% select(-Sexo_CVrisk, -Diabetes_bin, -Fumante_bin, -BP_Med_bin, -Statin_bin)
write.csv(dados_finais, caminho_saida, row.names = FALSE, na = "")
log(sprintf("\n%d linhas salvas em %s", nrow(dados), caminho_saida))

writeLines(
  c(
    sprintf("# Linhagem — %s", basename(caminho_saida)),
    "",
    sprintf("Gerado em %s a partir de `%s` + colunas P050/Q006 extraidas do Excel bruto da PNS.", format(Sys.time(), "%Y-%m-%dT%H:%M:%S"), basename(caminho_estagios)),
    "",
    "```",
    linhas_log,
    "```"
  ),
  caminho_log
)
cat(sprintf("Log de linhagem salvo em %s\n", caminho_log))
