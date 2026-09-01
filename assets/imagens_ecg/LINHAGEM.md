# Linhagem — Imagens de ECG (Parte 3)

| | |
|---|---|
| **Fonte** | Mendeley Data — *"ECG Images dataset of Cardiac Patients"*, Khan, Hussain & Malik (Ch. Pervaiz Elahi Institute of Cardiology, Multan, Paquistão) |
| **DOI** | [10.17632/gwbz3fsgp8.2](http://dx.doi.org/10.17632/gwbz3fsgp8.2) (versão 2 — versão atual no Mendeley em 2026-08-30) |
| **Licença** | Creative Commons Attribution 4.0 International (**CC BY 4.0**) — confirmado no campo `data_licence` da API pública do Mendeley Data |
| **Dispositivo de coleta** | ECG EDAN SERIES-3, unidades de terapia cardíaca de hospitais paquistaneses |
| **Data de extração** | 2026-08-30 |

## O que foi baixado

O dataset completo na origem tem **928 imagens** em 4 classes (615 MB no total). Para manter o repositório leve, foi baixada uma **amostra balanceada de 120 imagens (30 por classe)**, acima do mínimo de 100 imagens exigido pelo projeto, preservando a proporção entre as 4 classes originais:

| Classe (pasta) | Rótulo original no dataset | Total na fonte | Baixadas |
|---|---|---|---|
| `Normal` | Normal | 284 | 30 |
| `Infarto_Miocardio` | MI (Myocardial Infarction) | 239 | 30 |
| `Historico_Infarto_Miocardio` | PMI (Previous/History of MI) | 172 | 30 |
| `Batimento_Anormal` | HB (Abnormal Heartbeat) | 233 | 30 |

**Nota importante:** a versão 1 deste dataset (DOI `.1`, referenciada em parte da literatura como *"ECG Images dataset of Cardiac and COVID-19 Patients"*) tinha 1.937 imagens em 5 classes, incluindo uma classe COVID-19. A versão 2 (usada aqui, e a que está publicada atualmente no Mendeley) manteve apenas as 4 classes cardíacas e removeu a classe COVID-19 — por isso os números aqui divergem do que aparece em citações mais antigas do dataset.

## Reprodutibilidade

A lista completa dos 928 arquivos, com URL de download direto e hash SHA-256 de cada imagem, é obtida via API pública do Mendeley Data:

```
GET https://data.mendeley.com/public-api/datasets/gwbz3fsgp8
```

A amostra foi selecionada com `random.seed(42)`, 30 itens por classe via `random.sample`. O arquivo [`_manifest.json`](_manifest.json) desta pasta lista, para cada imagem efetivamente baixada: classe, nome do arquivo, tamanho em bytes e hash SHA-256 original (para conferência de integridade).

## Verificação de conteúdo e PII

Uma amostra foi inspecionada visualmente: cada imagem é um laudo de ECG de 12 derivações (formato "ECG REPORT") contendo apenas um ID numérico interno, sem nome, sem data de nascimento e sem endereço — os campos de idade/peso/altura do cabeçalho do laudo aparecem em branco no template. Consistente com a declaração do artigo de origem (Khan et al., *Data in Brief*, 2021) de que as imagens não carregam informação pessoal identificável do paciente.

## Estatísticas desta amostra

- Total de arquivos: 120
- Tamanho total: ~76 MB (79.518.971 bytes)
- Formato: `.jpg`
