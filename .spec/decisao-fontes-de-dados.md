# Decisão de Fontes de Dados — Por que 3 bases separadas, e não uma única

| | |
|---|---|
| **Projeto** | CardioIA — Fase 1 (Batimentos de Dados) |
| **Escopo** | Justificativa da arquitetura de dados das 3 partes (numérica, textual, visual) |
| **Status** | Investigação concluída — decisão confirmada. **Fonte numérica (Parte 1) trocada em 2026-08-31**, ver nota abaixo |
| **Última revisão** | 2026-08-31 |

---

> **Nota de revisão (2026-08-31):** este documento comparou originalmente NHANES contra PNS, MESA, HUNT, Lifelines etc. e escolheu **NHANES** (seção 3, tabela de bases numéricas) por ser a única gratuita, sem credenciamento e redistribuível. Essa comparação permanece válida para os critérios 1/2/6 (custo, acesso, redistribuição). Mas ela **não pesava viés de população** — e o NHANES representa a população dos EUA, não a do Brasil/SUS, alvo real do projeto. Ao reavaliar esse ponto, trocamos a fonte numérica para **PNS 2013 + módulo de exames laboratoriais (Fiocruz/ICICT, 2014-2015)**, que também é gratuita/redistribuível e, além disso, é população brasileira. Detalhes completos da nova fonte, variável por variável, em [`SDD-pipeline-pns-ckm.md`](SDD-pipeline-pns-ckm.md). As Partes 2 (texto) e 3 (imagem) não mudaram — a comparação de 19 bases abaixo continua válida para elas.

## 1. Pergunta que motivou a investigação

Antes de consolidar a arquitetura de 3 fontes descrita no [README](../README.md), investigamos se existia **uma única base pública** que cumprisse simultaneamente:

1. Gratuita;
2. Aberta para download direto (sem credenciamento moroso tipo PhysioNet Credentialed Access ou aplicação tipo UK Biobank);
3. Dados numéricos clínicos completos (pilares renal + metabólico + cardiovascular);
4. Textos médicos associados (laudos, notas clínicas, diretrizes);
5. ≥100 imagens cardíacas (ECG, ecocardiograma, ressonância/angiografia);
6. Licença que permita **redistribuir os arquivos livremente** (reupload em Google Drive/OneDrive público — requisito do enunciado da atividade);
7. Todas as variáveis necessárias para calcular **RCE** (Relação Cintura-Estatura) e os **3 eixos da Síndrome CKM** (metabólico, renal, cardiovascular).

Se essa base existisse, ela substituiria a fragmentação atual (NHANES + textos + imagens de fontes diferentes). Não encontramos nenhuma.

## 2. Metodologia

Levantamento desk research (documentação oficial, páginas de licença, papers de origem) de 19 bases candidatas, divididas em dois grupos: bases de coorte/EHR centradas em dado numérico, e bases centradas em imagem cardíaca. Cada candidata foi avaliada nos 7 critérios acima com fonte citada. Isto não substitui a leitura integral do Data Use Agreement de qualquer base antes do uso — serve como triagem para a decisão de arquitetura desta fase.

## 3. Candidatas — bases numéricas / coortes

| Dataset | 1. Gratuita | 2. Sem credenciamento | 3. Numérico renal+metab+CV completo | 4. Textos médicos | 5. ≥100 imagens cardíacas | 6. Redistribuição livre | 7. RCE + 3 eixos CKM |
|---|---|---|---|---|---|---|---|
| **NHANES** (CDC/NCHS) | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ domínio público | ✅ |
| **MIMIC-IV + MIMIC-IV-ECG** (PhysioNet) | ✅ | ❌ CITI training + credenciamento | ✅ | ✅ | ✅ (~800k ECGs) | ❌ DUA proíbe redistribuição | ⚠️ (completo, mas inacessível p/ reupload) |
| **eICU-CRD** (PhysioNet) | ✅ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ |
| **UK Biobank** | ❌ £9.000+IVA | ❌ aplicação formal | ✅ | ⚠️ | ✅ | ❌ Material Transfer Agreement | ✅ |
| **Framingham** (BioLINCC) | ✅ | ⚠️ IRB + acordo | ✅ | ❌ | ⚠️ | ❌ | ✅ |
| **All of Us** (NIH) | ✅ | ❌ Researcher Workbench | ✅ | ✅ | ⚠️ | ❌ política proíbe explicitamente | ✅ |
| **MESA / Jackson Heart / CARDIA** (BioLINCC) | ✅ | ⚠️ IRB + acordo | ✅ | ❌ | ✅ (MESA tem CMR) | ❌ | ✅ |
| **CODE-15%** (Zenodo) | ✅ | ✅ | ❌ só idade/sexo | ❌ | ✅ (sinal, não imagem) | ✅ CC BY 4.0 | ❌ |
| **PTB-XL** (PhysioNet) | ✅ | ✅ | ❌ sem labs renais/metabólicos | ⚠️ laudo curto por exame | ✅ (sinal) | ✅ CC BY 4.0 | ❌ falta cintura/labs |

## 4. Candidatas — bases de imagem cardíaca

| Dataset | Modalidade | 1. Gratuito | 2. Download direto | 3. Labs renal+metab+CV | 4. Textos médicos | 5. N imagens | 6. Licença | 7. RCE+3 eixos CKM |
|---|---|---|---|---|---|---|---|---|
| **Mendeley — ECG Images dataset of Cardiac Patients** (Khan, Hussain & Malik — fonte escolhida, Parte 3) | ECG imagem | ✅ | ✅ | ❌ nenhum dado de paciente | ❌ | 928, 4 classes, v2 (confirmado via API pública, ver §6) | ✅ **CC BY 4.0 confirmado** (`data_licence` da API) | ❌ |
| **PTB-XL / PTB-XL+** | ECG sinal | ✅ | ✅ | ❌ | ✅ laudo textual | N/A (sinal) | ✅ CC BY 4.0 | ❌ |
| **Chapman-Shaoxing-Ningbo** (PhysioNet) | ECG sinal | ✅ | ✅ | ❌ só idade/sexo | ❌ | N/A (sinal) | ✅ CC BY 4.0 | ❌ |
| **EchoNet-Dynamic / Pediatric** (Stanford) | Ecocardiograma vídeo | ⚠️ registro | ⚠️ | ❌ só EF/VDF/VSF | ❌ | 10.030 / 7.643 | ❌ Research Use Only | ❌ |
| **ACDC** (RM cardíaca) | RM cardíaca | ✅ | ⚠️ registro | ⚠️ peso/altura só | ❌ | 150 exames | ⚠️ uso acadêmico c/ citação | ⚠️ parcial |
| **Sunnybrook Cardiac Data** (RM cardíaca) | RM cardíaca | ✅ | ✅ | ❌ só categoria | ❌ | 45 pacientes / 805 imagens | ✅ **CC0 1.0** | ❌ |
| **UCI Heart Disease (Cleveland)** | — | ✅ | ✅ | ⚠️ | ❌ | 0 (desqualificado) | ✅ | N/A |
| **CheXpert / MIMIC-CXR** | Rx tórax (não cardíaco-específico) | ⚠️/❌ | ⚠️ | ❌ | ⚠️ | >200k (fora de escopo) | ⚠️ | ❌ |
| **SBC diretrizes / ABC Cardiol (SciELO) / BVS** | Texto (não imagem) | ✅ | ✅ | N/A | ✅ artigos ABC Cardiol **CC BY 4.0** (diretriz de IC) / **CC BY-NC** (revisão de síndrome cardiorrenal) — fontes efetivamente usadas, ver §6 | 0 | ✅ CC BY / CC BY-NC (artigos ABC Cardiol via SciELO) — **diretrizes em PDF direto do site da SBC não têm essa garantia** | N/A — corpus textual complementar |

## 5. Achado estrutural

As 19 bases avaliadas se dividem em dois grupos, e nenhuma atravessa a fronteira:

- **Abertas e redistribuíveis, mas clinicamente incompletas**: NHANES (números completos, zero imagem/texto), PTB-XL/CODE-15%/Chapman-Shaoxing (ECG livre, mas sem labs renais/metabólicos), Mendeley/Kaggle ECG (imagem livre, zero variável numérica), Sunnybrook (imagem livre, zero dado clínico).
- **Clinicamente completas, mas fechadas por credenciamento e com redistribuição proibida por contrato**: MIMIC-IV(+ECG) (a mais completa — números + laudos + ECG), UK Biobank, All of Us, MESA/BioLINCC. Em todas, o Data Use Agreement ou Material Transfer Agreement veda explicitamente reupload/redistribuição pública.

Não existe hoje uma base pública que combine as duas colunas.

## 6. Decisão

Mantemos a arquitetura de **3 fontes independentes**, já descrita no README:

| Parte | Fonte | Licença/base legal |
|---|---|---|
| 1 — Numérica | ~~NHANES 2017-2018 (CDC/NCHS)~~ → **PNS 2013 + exames laboratoriais (Fiocruz/ICICT)**, trocado em 2026-08-31 por viés de população (ver nota de revisão no topo deste documento) | Lei de Acesso à Informação + Dados Abertos IBGE, download livre sem cadastro |
| 2 — Textual | **Executado.** *Diretriz Brasileira de Insuficiência Cardíaca Crônica e Aguda* (SBC/DEIC, SciELO/Arq Bras Cardiol 2018) + revisão sistemática *"Síndrome Cardiorrenal Aguda..."* (Leite et al., Arq Bras Cardiol 2020) — ambas publicadas na SciELO, não PDF direto do site institucional da SBC | CC BY 4.0 (diretriz de IC) e CC BY-NC (revisão de síndrome cardiorrenal), confirmadas nas próprias páginas dos artigos |
| 3 — Visual | **Executado.** Mendeley Data — *"ECG Images dataset of Cardiac Patients"* (Khan, Hussain & Malik), versão 2, DOI 10.17632/gwbz3fsgp8.2 | CC BY 4.0 confirmado via API pública do Mendeley (`data_licence`) — 928 imagens na fonte, 4 classes (Normal / MI / PMI-histórico de infarto / HB-batimento anormal); amostra balanceada de 120 imagens (30/classe) baixada para o repositório — ver `assets/imagens_ecg/LINHAGEM.md` |

Esta é a única combinação, dentre as 19 avaliadas, que satisfaz simultaneamente gratuidade, ausência de credenciamento moroso e liberdade de redistribuição — as bases clinicamente mais ricas (MIMIC-IV, UK Biobank, All of Us, MESA) falham exatamente nesses critérios por desenho contratual, não por acaso.

## 7. Limitação assumida (importante para a seção de Governança do README)

**As três fontes não compartilham os mesmos indivíduos.** O paciente da imagem de ECG (hospitais paquistaneses, dataset Mendeley) não é o mesmo participante do NHANES (EUA) nem está descrito em nenhum trecho da diretriz textual da SBC. A combinação das 3 partes no projeto CardioIA é **pedagógica/sintética** — cada parte demonstra separadamente uma competência de governança sobre um tipo de dado (numérico, textual, visual), mas não constitui uma coorte real unificada. Isso deve ficar explícito na seção de Governança/Viés do README para evitar a impressão de que existe um vínculo real entre o CSV numérico e as imagens de ECG.

## 8. Fontes consultadas

- [NHANES III ECG manual](https://wwwn.cdc.gov/nchs/data/nhanes3/manuals/ecg.pdf) e [NHANES III data files](https://wwwn.cdc.gov/nchs/nhanes/nhanes3/datafiles.aspx) — confirma descontinuação do componente de ECG desde 1999
- [MIMIC-IV v2.2 (PhysioNet)](https://physionet.org/content/mimiciv/2.2/)
- [PhysioNet Credentialed Access — guia](https://casrai.org/guides/physionet-credentialed-access-restricted-data)
- [eICU-CRD — licença](https://physionet.org/content/eicu-crd/view-license/2.0/)
- [UK Biobank — tabela de taxas](https://www.ukbiobank.ac.uk/use-our-data/fees/) e [Material Transfer Agreement](https://www.ukbiobank.ac.uk/media/5cclro0y/applicant-mta-data-only-2021.pdf)
- [BioLINCC — guia do usuário](https://biolincc.nhlbi.nih.gov/media/BioLINCC_User_Guide_05Jan2026.pdf), [Framingham](https://biolincc.nhlbi.nih.gov/studies/framcohort/), [MESA](https://biolincc.nhlbi.nih.gov/studies/mesa/), [CARDIA](https://biolincc.nhlbi.nih.gov/studies/cardia/)
- [All of Us — níveis de acesso a dados](https://www.researchallofus.org/data-tools/data-access/) e [políticas para pesquisadores](https://support.researchallofus.org/hc/en-us/articles/4415498292244)
- [CODE-15% (Zenodo)](https://zenodo.org/records/4916206) e [artigo CODE (Global Heart)](https://globalheartjournal.com/articles/10.5334/gh.1554)
- [PTB-XL — LICENSE.txt](https://physionet.org/content/ptb-xl/1.0.3/LICENSE.txt) e [paper (Scientific Data)](https://www.nature.com/articles/s41597-020-0495-6)
- Mendeley Data — Khan, Hussain & Malik, *"ECG Images dataset of Cardiac Patients"* (v2, DOI [10.17632/gwbz3fsgp8.2](http://dx.doi.org/10.17632/gwbz3fsgp8.2)) — API pública `https://data.mendeley.com/public-api/datasets/gwbz3fsgp8` usada para confirmar licença, contagem por classe e obter URLs de download
- [Diretriz Brasileira de Insuficiência Cardíaca Crônica e Aguda (SciELO/ABC)](https://www.scielo.br/j/abc/a/XkVKFb4838qXrXSYbmCYM3K/) — DOI [10.5935/abc.20180190](https://doi.org/10.5935/abc.20180190)
- [Síndrome Cardiorrenal Aguda: Qual Critério Diagnóstico Utilizar... (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8384316/) — DOI 10.36660/abc.20190207

## 9. Histórico de revisões

| Data | Mudança |
|---|---|
| 2026-08-30 | Documento criado a partir da investigação comparativa de 19 bases candidatas; decisão confirmada de manter as 3 fontes já descritas no README. |
| 2026-08-30 | Partes 2 e 3 executadas: textos reais extraídos (SciELO) e 120 imagens de ECG baixadas (Mendeley, v2 — corrigido de v1/1.937 imagens/5 classes, citada na investigação inicial, para v2/928 imagens/4 classes, versão atualmente publicada). |
| 2026-08-31 | Fonte numérica (Parte 1) trocada de NHANES para PNS 2013 + exames laboratoriais (Fiocruz/ICICT), para eliminar o viés de população EUA-vs-Brasil identificado na seção de Governança do README. NHANES removido do repositório (`src/build_nhanes_ckm_dataset.py`, dados e SDD antigo). Ver [`SDD-pipeline-pns-ckm.md`](SDD-pipeline-pns-ckm.md) para a justificativa completa e o novo dicionário de dados. |
