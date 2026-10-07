---
name: registrar-decisao
description: >
  Cria Clinical Decision Records (CDRs) para documentar decisões clínicas sobre a base
  de conhecimento — mudanças de peso, novas associações polêmicas, ajustes no golden,
  pendências de validação pela Dra. Fernanda. Adaptação de create-adr (TLC) para o domínio
  clínico do CardioIA. Use quando pedir "registrar-decisao", "documente essa decisão",
  "crie um CDR", "registre a mudança clínica", "documente por que mudamos o peso",
  "registre essa pendência da supervisora", "write an ADR for this clinical change".
  NÃO use para decisões técnicas de engenharia (use create-adr padrão), para code review
  (use revisor-clinico) ou para questionar uma decisão (use devil-advocate).
license: CC-BY-4.0
metadata:
  baseado_em: tech-leads-club/agent-skills:(creation)/create-adr
  adaptado_por: CardioIA Grupo S — FIAP
  versao: 1.0.0
---

# Registrar Decisão Clínica (CDR)

Documenta decisões clínicas sobre a base de conhecimento do CardioIA como **CDRs —
Clinical Decision Records**. Um CDR responde a uma pergunta que o time terá daqui a
seis meses: "por que tomamos essa decisão e quem a aprovou clinicamente?"

CDRs ficam em `.spec/decisions/cdr-NNN-kebab-case.md`.

---

## Quando criar um CDR

Crie um CDR sempre que uma das seguintes situações ocorrer:

- Mudança de peso (`peso`) em `mapa_conhecimento.csv` ou `associacoes.csv`
- Nova associação polêmica ou sem consenso imediato (tipo_relacao controverso)
- Ajuste em `tests/golden/relatos_esperados.json` que muda uma condição esperada
- Decisão de **não** incluir um sintoma/conceito apesar de solicitação
- Pendência de validação clínica registrada — decisão tomada provisoriamente pelo time,
  aguardando confirmação da Dra. Fernanda
- Mudança no threshold do classificador ou na métrica primária

---

## Fluxo de Trabalho

### Etapa 1: Coletar contexto

Antes de escrever, responder:

1. **O que mudou exatamente?** (arquivo:linha ou registro específico)
2. **Por que a mudança foi necessária?** (qual problema clínico ou técnico motivou)
3. **Quais alternativas foram consideradas e descartadas?**
4. **Qual é o status de validação clínica?**
   - `aprovado` — Dra. Fernanda confirmou explicitamente
   - `pendente` — time decidiu, aguarda confirmação da supervisora
   - `recusado` — decidiu-se não fazer
5. **Qual o impacto no conjunto de teste congelado?** (se houver, é uma parada obrigatória)

Se algum desses pontos for desconhecido, perguntar ao usuário antes de redigir.

### Etapa 2: Determinar o número do CDR

```bash
ls .spec/decisions/cdr-*.md 2>/dev/null | sort | tail -1
# se vazio, começar em cdr-001
```

Próximo número = último + 1, com zero-padding de 3 dígitos.

### Etapa 3: Criar o arquivo

Caminho: `.spec/decisions/cdr-NNN-kebab-curto.md`

Onde `kebab-curto` é 2–5 palavras que identificam a decisão (ex: `peso-ic-edema`,
`adicionar-oliguria-cardiorrenal`, `threshold-recall-090`).

### Etapa 4: Preencher o template

Ver template abaixo — preencher todas as seções; a única seção opcionalmente vazia é
"Alternativas descartadas" quando só havia uma opção viável (indicar por quê).

### Etapa 5: Registrar no índice

Adicionar uma linha ao arquivo `.spec/decisions/INDEX.md` (criá-lo se não existir):

```
| CDR-NNN | [título curto] | [status] | [data] |
```

### Etapa 6: Atualizar o campo `observacao` do CSV

Se o CDR documenta uma mudança numa linha de CSV, atualizar o campo `observacao` do
registro afetado para referenciar o CDR:

```
Pendente de validação clínica (CDR-NNN). Dra. Fernanda a consultar.
```

---

## Template CDR

```markdown
# CDR-NNN — [Título da Decisão em PT-BR]

**Data:** AAAA-MM-DD
**Status:** pendente / aprovado / recusado
**Validação clínica:** pendente (Dra. Fernanda Fassina, CRM-SP 169944) / aprovado em [data] / não requer
**Responsável no time:** [nome ou "Grupo S"]
**Arquivos afetados:** [lista de arquivos:linha]

---

## Contexto

[2–4 parágrafos explicando a situação que levou à decisão. Qual era o comportamento
antes? Qual problema clínico ou técnico foi identificado? Qual evidência motivou a mudança?]

## Decisão

[Uma frase afirmativa e direta: "Decidimos [ação] porque [razão principal]."
Depois, detalhes operacionais: o que exatamente mudou, quais valores, quais registros.]

## Consequências

### Positivas
- [lista]

### Negativas / Riscos
- [lista — ser honesto; se há risco clínico, nomear]

### Impacto no conjunto de teste
[Descrever se afeta `particao=teste` e como foi tratado. Se o conjunto congelado não
foi tocado, escrever explicitamente: "O conjunto de teste manual não foi modificado."]

## Alternativas descartadas

| Alternativa | Por que descartada |
|---|---|
| [opção 1] | [razão] |

## Pendências de validação

[Lista do que ainda precisa ser confirmado pela Dra. Fernanda ou pela literatura clínica.
Deixar em branco apenas se status = "aprovado" e nada ficou pendente.]

---

*CDR do CardioIA — formato adaptado de Architecture Decision Records (ADR).*
*Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).*
```

---

## Exemplos

### Exemplo 1 — Mudança de peso de associação

**Usuário:** "Mudamos o peso de IC↔edema de 0.7 para 0.9 porque o RELATO 08 estava
empatando. A Dra. Fernanda não confirmou ainda."

**Ações:**
- Determinar número: CDR-001 (primeiro CDR)
- Nome do arquivo: `cdr-001-peso-ic-edema.md`
- Status: `pendente`
- Arquivos afetados: `fase2/knowledge_base/associacoes.csv:linha_do_AS029`
- Atualizar `observacao` do AS029 para referenciar CDR-001

### Exemplo 2 — Decisão de não incluir síntoma

**Usuário:** "Decidimos não incluir 'dor nas costas' como expressão de dor torácica
porque pode confundir com lombalgia."

**Ações:**
- Status: `aprovado` (decisão do time, sem necessidade de supervisora para exclusão)
- Documentar alternativa descartada: inclusão com baixo peso
- Consequência negativa: recall pode ser menor em IAM com irradiação dorsal

---

## Regras de Governança

- CDRs são **imutáveis após criação**: adicionar notas de atualização ao final do arquivo
  (seção `## Atualizações`), nunca editar o corpo original.
- Status `pendente` deve ter prazo implícito: mencionar na seção "Pendências" até quando
  espera-se confirmação.
- Se a supervisora recusar uma decisão pendente, criar um novo CDR com status `recusado`
  e referenciar o CDR original — não deletar.
- CDRs de conjunto de teste congelado exigem aprovação explícita da equipe inteira
  antes de serem lavrados (CLAUDE.md §2).

---

## Aviso Clínico

⚠️ AVISO CLÍNICO: Este sistema é um protótipo acadêmico e NÃO substitui avaliação médica.
Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).
