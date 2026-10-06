# CardioIA --- Base de Conhecimento Textual

Esta pasta contém a base de conhecimento textual da Fase 2. **Não é o
banco de dados clínico da Fase 1.**

## Arquivos

-   `conceitos.csv`: vocabulário clínico normalizado.
-   `expressoes.csv`: formas simuladas de o paciente expressar os
    conceitos.
-   `atributos.csv`: posição, esforço, repouso, duração, irradiação,
    temporalidade e outros contextos.
-   `associacoes.csv`: relações entre conceitos, condições, atributos e
    fontes.
-   `fontes.csv`: rastreabilidade científica.
-   `mapa_conhecimento.csv`: visão **derivada** no formato do enunciado
    (`sintoma_1,sintoma_2,doenca_associada`), gerada a partir dos cinco
    arquivos acima. Não edite à mão.

## Como editar

1.  Edite os CSVs normalizados (IDs são imutáveis; novos registros
    recebem o próximo ID).
2.  Regenere o mapa: `python fase2/src/gerar_mapa_conhecimento.py`.
3.  Rode o contrato: `python -m pytest fase2/tests/test_base_conhecimento.py fase2/tests/test_mapa_conhecimento.py`
    (no Claude Code isso roda sozinho, via hook, a cada edição).

O contrato completo está no SDD (`.spec/SDD-fase2-nlp-triagem.md`, §3).

## Regra central

A base evita relações simplistas como
`falta de ar = insuficiência cardíaca`.

O modelo é:

`expressão → conceito + contexto/atributos → associações possíveis`

As associações clínicas vêm das fontes. As frases com
`origem_expressao=simulada` foram criadas para NLP e **não são citações
literais da literatura**.

## Cardiorrenal

Edema, oligúria e dispneia podem participar de contextos de
congestão/disfunção cardiorrenal, mas não são suficientes isoladamente
para diagnosticar síndrome cardiorrenal. A interpretação futura deve
poder integrar dados clínicos/laboratoriais.

## Estrutura

``` text
knowledge_base/
├── conceitos.csv
├── expressoes.csv
├── associacoes.csv
├── atributos.csv
├── fontes.csv
├── mapa_conhecimento.csv   (derivado)
└── README.md
```

## Revisão v1.1

A revisão de consistência manteve os 21 conceitos, 73 expressões, 23 atributos e 28 associações.

Ajuste realizado:
- `A012` passou a representar exclusivamente **duração maior que 20 minutos**. A expressão genérica `não passa` foi removida desse atributo porque descreve persistência/ausência de alívio, não prova uma duração específica.

Regras preservadas:
- sintomas compartilhados não determinam uma doença isoladamente;
- sintomas menos típicos de insuficiência cardíaca permanecem marcados como menos típicos;
- edema/oligúria/dispneia não determinam síndrome cardiorrenal;
- as expressões simuladas não são apresentadas como citações científicas;
- atributos de dor torácica devem ser combinados com o contexto, e não usados como diagnóstico automático.

## Revisão v1.2

A base passou a ter 21 conceitos, 99 expressões, 23 atributos, 29 associações e 7 fontes (o mapa achatado tem 82 linhas).

Correções de estrutura:
- `AS023` e `AS024` tinham uma vírgula a mais, que deixava a coluna `observacao` vazia.
- `AS012` usava a condição `Insuficiência Cardíaca / contexto cardiorrenal`, que duplicava a IC. Passou a `Insuficiência Cardíaca` / `sintoma menos típico`, que é como a F001 classifica a oligúria. O contexto cardiorrenal da oligúria continua em `AS027`.

Correções clínicas — **pendentes de validação pela Dra. Fernanda Fassina**:
- `AS013` (dor torácica → IAM/SCA) passou a considerar o padrão em crescendo (`A011`, `A021`–`A023`): dor que piora, aparece com esforço menor ou em repouso é angina instável, que faz parte da SCA (F002/F003). Isso resolve o empate IAM × Angina do RELATO 07.
- `AS029` (nova): edema periférico → Insuficiência Cardíaca, como sintoma menos típico. Na F001, edema periférico é um sinal menos específico de IC.

Correções de viés de gênero (contrato de paridade, SDD §3, regra 10). As expressões só existiam no masculino, então a mesma queixa escrita por uma mulher não era reconhecida. Foram incluídas:
- `E098` "me deixando mais cansada";
- `E099` "respiração piora deitada";
- em `A001`, `A002`, `A004` e `A005`, os gatilhos "quando estou deitada", "deitada para dormir", "estava sentada", "ficar sentada", "sentada na cama", "quando fico nervosa", "estando parada" e "mesmo estando parada".
