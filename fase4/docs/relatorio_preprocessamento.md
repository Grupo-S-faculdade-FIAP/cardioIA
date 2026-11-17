# Relatório — Pré-processamento de imagens de ECG (Fase 4 · Parte 1)

> ⚠️ **AVISO CLÍNICO:** Este sistema é um protótipo acadêmico e **NÃO** substitui avaliação médica.
> Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).

**Equipe:** Grupo S — FIAP (Caroline Corrêa, Enzo Sader, Lucas Koyama, Rodrigo Figueiroa, Tiago Curi)  
**Notebook:** [`../notebooks/01_preprocessamento.ipynb`](../notebooks/01_preprocessamento.ipynb)  
**Linhagem:** [`../data/imagens_ecg_completo_LINHAGEM.md`](../data/imagens_ecg_completo_LINHAGEM.md)

---

## 1. Escolha do dataset

Optamos pelo *ECG Images dataset of Cardiac Patients* (Mendeley Data, v2, DOI `10.17632/gwbz3fsgp8.2`, licença **CC BY 4.0**), a mesma fonte já catalogada na Fase 1 do CardioIA. Motivos:

1. **Continuidade clínica do projeto** — classes cardíacas (Normal, MI, PMI, HB) alinhadas ao foco em risco cardiovascular / CKM, em vez de migrar para tórax (NIH Chest X-rays).
2. **Governança já documentada** — licença redistribuível, API pública com hashes SHA-256, inspeção de PII feita na Fase 1.
3. **Volume adequado à disciplina** — ~928 laudos JPG de 12 derivações (~615 MB), suficiente para treinar/comparar CNNs em Colab sem exigir credenciamento hospitalar.

A amostra de 120 imagens em `assets/imagens_ecg/` permanece intacta; a Fase 4 baixa o conjunto **completo** para `fase4/data/imagens_ecg_completo/` (fora do Git).

## 2. Etapas do pipeline

| Etapa | Decisão | Justificativa |
|---|---|---|
| Organização | Pastas por classe (`Normal`, `Infarto_Miocardio`, `Historico_Infarto_Miocardio`, `Batimento_Anormal`) | Mesmo vocabulário da Fase 1; facilita `flow_from_directory`. |
| Espaço de cor | BGR→RGB, 3 canais | VGG16 ImageNet espera RGB; laudos já são coloridos. |
| Redimensionamento | **224×224** (INTER_AREA) | Resolução nativa padrão do VGG16; reduz custo de GPU mantendo o laudo legível o bastante para um protótipo. |
| Normalização | Pixels em **[0, 1]** | Escala estável para CNN do zero; no gerador Keras usamos `rescale=1/255`. |
| Split | **70% / 15% / 15%**, estratificado, `random_state=42` | Reprodutibilidade (regra do projeto); validação para early stopping; teste só no relatório final. |
| Augmentation (só treino) | Rotação ±8°, zoom ±10%, brilho 0,9–1,1; **sem flip horizontal** | Flip espelharia derivações e invalidaria a geometria do traçado; distorções leves simulam variação de captura sem inventar morfologia clínica. |

O manifesto `data/processado/manifesto_split.csv` (e `.json`) registra arquivo, classe, partição e hash de cada imagem processada.

## 3. Limitações (transparência)

- Trabalhamos com a **imagem do laudo completo**, não com recortes por derivação: o modelo pode aprender atalhos visuais do template (cabeçalho, grade) além da morfologia do ECG.
- Classes **MI** e **PMI** são visualmente próximas; erros entre elas são esperados e devem ser lidos como limitação do protótipo, não como laudo.
- Reduzir de ~2213×1572 para 224×224 descarta detalhe fino do traçado — trade-off consciente entre fidelidade e viabilidade de treino em aula/Colab.
- Dados são de população paquistanesa (fonte original); não representam o SUS brasileiro.

## 4. Reprodutibilidade

```bash
python fase4/data/baixar_ecg_mendeley.py
python fase4/src/pipeline_imagens.py
```

Seed fixo **42** em splits e geradores. Nenhum dado identificável de paciente do CardioIA é utilizado.
