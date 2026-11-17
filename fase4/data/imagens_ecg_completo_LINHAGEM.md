# Linhagem — Imagens de ECG (Fase 4, dataset completo)

| | |
|---|---|
| **Fonte** | Mendeley Data — *"ECG Images dataset of Cardiac Patients"*, Khan, Hussain & Malik (Ch. Pervaiz Elahi Institute of Cardiology, Multan, Paquistão) |
| **DOI** | [10.17632/gwbz3fsgp8.2](http://dx.doi.org/10.17632/gwbz3fsgp8.2) (versão 2) |
| **Licença** | Creative Commons Attribution 4.0 International (**CC BY 4.0**) |
| **Dispositivo de coleta** | ECG EDAN SERIES-3 |
| **Responsável pela obtenção** | Equipe Grupo S — FIAP (CardioIA) |
| **Script** | [`baixar_ecg_mendeley.py`](baixar_ecg_mendeley.py) |
| **Destino local** | `fase4/data/imagens_ecg_completo/` (**não versionado** no Git; ~615 MB) |

## Relação com a amostra da Fase 1

A Fase 1 versionou uma **amostra balanceada de 120 imagens** (30 por classe) em [`assets/imagens_ecg/`](../../assets/imagens_ecg/), com seed 42. A Fase 4 usa o **conjunto completo** da mesma fonte (~928 JPGs) para treinar e avaliar CNNs. As duas pastas coexistem; a amostra da Fase 1 **não é alterada**.

## Classes e volumes na fonte

| Classe (pasta CardioIA) | Prefixo no arquivo | Total na fonte |
|---|---|---:|
| `Normal` | `Normal` | 284 |
| `Infarto_Miocardio` | `MI` | 239 |
| `Historico_Infarto_Miocardio` | `PMI` | 172 |
| `Batimento_Anormal` | `HB` | 233 |
| **Total** | | **928** |

## Como obter / reproduzir

```bash
# a partir da raiz do repositório
python fase4/data/baixar_ecg_mendeley.py
```

O script consulta a API pública:

```
GET https://data.mendeley.com/public-api/datasets/gwbz3fsgp8
```

e baixa cada JPG para `imagens_ecg_completo/<Classe>/`, validando o SHA-256 informado pela API. Gera `_manifest_completo.json` com classe, nome, bytes e hash de cada arquivo.

## Critérios de inclusão

- Apenas arquivos `.jpg` da versão 2 do dataset (sem a classe COVID-19 da v1).
- Sem filtragem adicional de qualidade: todas as 928 imagens da API entram no pipeline.
- Partições treino / validação / teste (70% / 15% / 15%, estratificadas, `random_state=42`) são criadas no pré-processamento — ver `fase4/data/processado/` e o notebook `01_preprocessamento.ipynb`.

## Privacidade

Inspeção visual (Fase 1) e declaração dos autores: laudos sem PII identificável do paciente (campos de idade/peso/altura em branco no template; só ID interno). Uso estritamente acadêmico no CardioIA.

## Aviso clínico

> ⚠️ **AVISO CLÍNICO:** Este sistema é um protótipo acadêmico e **NÃO** substitui avaliação médica.
> Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).
