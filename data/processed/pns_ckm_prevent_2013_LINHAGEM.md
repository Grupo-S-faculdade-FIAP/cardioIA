# Linhagem — pns_ckm_prevent_2013.csv

Gerado em 2026-08-31T19:57:52 a partir de `pns_ckm_estagios_2013.csv` + colunas P050/Q006 extraidas do Excel bruto da PNS.

```
Lendo bruto (P050 tabagismo, Q006 uso de anti-hipertensivo): C:/Users/caroo/OneDrive/Desktop/FIAP/projetos/cardioIA/data/raw/pns_2013_exames/EXAMES-PNS-2013-FINAL_05052023.xlsx
Lendo dataset com estagios ja calculados: C:/Users/caroo/OneDrive/Desktop/FIAP/projetos/cardioIA/data/processed/pns_ckm_estagios_2013.csv
8952 linhas de cada lado, alinhadas por posicao
Uso_Anti_Hipertensivo: 6423 NA recodificados para 'Nao' (ausencia logica — sem diagnostico de hipertensao)
Fumante_Atual: 1294 Sim, 7650 Nao, 8 NA
Uso_Anti_Hipertensivo: 1687 Sim, 6839 Nao, 426 NA
Calculando risco PREVENT (10 anos) — so para 30-79 anos com as 11 variaveis completas...
Risco PREVENT calculado para 5128 de 8952 pessoas (57.3%) — o resto ficou fora da faixa 30-79 anos ou tinha alguma variavel de entrada ausente

Distribuicao de CKM_Stage_Com_PREVENT (agora com Estagio 3 real, via criterio PREVENT):
  0: 1364 (15.2%)
  1: 2264 (25.3%)
  2: 4914 (54.9%)
  3: 15 (0.2%)
  4: 395 (4.4%)

8952 linhas salvas em C:/Users/caroo/OneDrive/Desktop/FIAP/projetos/cardioIA/data/processed/pns_ckm_prevent_2013.csv
```
