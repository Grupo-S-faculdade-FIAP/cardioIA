# Linhagem — pns_ckm_estagios_2013.csv

Gerado em 2026-08-31T17:08:51 a partir de `pns_ckm_rce_2013.csv`, aplicando `.spec/especificacao-estagios-ckm.md`.

```
Base de entrada: pns_ckm_rce_2013.csv — 8952 linhas
Insuficiencia_Cardiaca: 8548 NaN recodificados para 'Nao' (ausência lógica, ver docs/eda-pns-2013-achados.md)
Doenca_Coronariana: 8548 NaN recodificados para 'Nao' (ausência lógica, ver docs/eda-pns-2013-achados.md)
Infarto_Miocardio: 8548 NaN recodificados para 'Nao' (ausência lógica, ver docs/eda-pns-2013-achados.md)
Sindrome_Metabolica_Parcial calculada só com os 4 critérios completos: 8205 de 8952 pessoas (91.7%)

Distribuição de CKM_Stage (estágio 3 não existe nesta base — ver docstring do script):
  0.0: 1364 (15.2%)
  1.0: 2264 (25.3%)
  2.0: 4929 (55.1%)
  4.0: 395 (4.4%)

Distribuição dos classificadores da Camada 3:
  Obesidade: {'Nao': np.int64(6913), 'Sim': np.int64(1942), nan: np.int64(97)}
  Obesidade_Central: {'Sim': np.int64(6720), 'Nao': np.int64(2135), nan: np.int64(97)}
  Classificacao_Glicemica: {'Normal': np.int64(6363), 'Pre_Diabetes': np.int64(1319), 'Diabetes': np.int64(887), nan: np.int64(383)}
  Hipertensao_CKM: {'Sim': np.int64(4897), 'Nao': np.int64(3963), nan: np.int64(92)}
  Dislipidemia: {'Nao': np.int64(5037), 'Sim': np.int64(3557), nan: np.int64(358)}
  Sindrome_Metabolica_Parcial: {'Nao': np.int64(6339), 'Sim': np.int64(1866), nan: np.int64(747)}
  Categoria_KDIGO_G: {'G1': np.int64(5530), 'G2': np.int64(2548), nan: np.int64(417), 'G3a': np.int64(337), 'G3b': np.int64(87), 'G5': np.int64(17), 'G4': np.int64(16)}

8952 linhas salvas em C:\Users\caroo\OneDrive\Desktop\FIAP\projetos\cardioIA\data\processed\pns_ckm_estagios_2013.csv
```
