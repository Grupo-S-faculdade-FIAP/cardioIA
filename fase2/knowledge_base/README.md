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
└── README.md
```

## Próximas etapas

1.  Revisão final da base.
2.  Criar 10 relatos simulados em `relatos_pacientes.txt`.
3.  Implementar a extração em Python.
4.  Criar dataset separado de risco.
5.  TF-IDF + classificador.
6.  Avaliar erros e vieses.
7.  Depois, avaliar embeddings/modelos neurais.

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
