library(lubridate)
library(readxl)
library(ggplot2)
library(dplyr)
library(tidyverse)


dados_br <- read.csv(
  "C:/Users/caroo/OneDrive/Desktop/FIAP/projetos/cardioIA/data/processed/pns_ckm_rce_2013.csv",
  na.strings = c("NA", "")
)

detectar_outliers_iqr <- function(x) {
  q1 <- quantile(x, 0.25, na.rm = TRUE)
  q3 <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  x < (q1 - 1.5 * iqr) | x > (q3 + 1.5 * iqr)
}

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

t(sapply(dados_br[variaveis_numericas], resumir_outliers))
