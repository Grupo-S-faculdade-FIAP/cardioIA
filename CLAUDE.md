# CardioIA — Regras do Projeto

> CDSS acadêmico para triagem precoce de síndrome CKM (cardiorrenal-metabólica).  
> Supervisão clínica: **Dra. Fernanda Fassina** (CRM-SP 169944).

---

## 1. Idioma e tom

- **Textos voltados a pacientes, base de conhecimento e relatórios clínicos** → sempre em PT-BR.
- **Código-fonte, commits, docstrings** → PT-BR para comentários narrativos; nomes de variáveis/funções em PT-BR quando o domínio é clínico (ex: `extrair_conceitos`, `calcular_metricas`).
- **Documentos técnicos (SDD, ADRs, CLAUDE.md)** → PT-BR.

## 2. Dados de pacientes

- **Jamais usar dados reais de pacientes.** Todos os relatos e frases são sintéticos ou anonimizados.
- Todo dataset deve ter um arquivo `<dataset>_LINHAGEM.md` na mesma pasta (padrão da Fase 1), descrevendo: origem, método de geração, responsável, data e critérios de inclusão.
- O conjunto de **teste manual** (`particao=teste`, `origem=manual`) é **intocável após criação**: nunca adicionar, editar ou remover linhas sem aprovação explícita da equipe + revisão da Dra. Fernanda.

## 3. Avisos clínicos obrigatórios

Qualquer saída do sistema para uso externo (notebook exportado, relatório, README público) deve incluir:

```
⚠️ AVISO CLÍNICO: Este sistema é um protótipo acadêmico e NÃO substitui avaliação médica.
Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).
```

## 4. Reprodutibilidade

- **Seed fixo = 42** em todo código que envolva aleatoriedade (`random_state=42`, `SEED = 42`).
- Nunca usar `random_state=None` ou omitir o seed em modelos scikit-learn.
- Splits de dados devem ser reprodutíveis; usar `stratify=y` quando possível.

## 5. Estrutura de arquivos — Fase 2

```
fase2/
  config/           ← metas_avaliacao.json
  data/             ← relatos_pacientes.txt, frases_risco.csv (+ _LINHAGEM.md), casos_comportamento.csv
  knowledge_base/   ← 5 CSVs normalizados (conceitos, expressoes, atributos, associacoes, fontes)
                       + mapa_conhecimento.csv (DERIVADO — não editar à mão)
  notebooks/        ← 01_extracao_sintomas.ipynb, 02_classificador_risco.ipynb, 03_analise_vieses.ipynb
  reports/          ← metricas_todos.json gerado por avaliacao.py (versionado: é o resultado oficial)
  src/              ← extrator_sintomas.py, analisador_clinico.py, carregador_base.py, main.py,
                       gerar_mapa_conhecimento.py, vieses.py, contrato_dataset.py, avaliacao.py
  tests/            ← um arquivo por contrato/requisito do SDD + conftest.py + golden/
```

## 6. Base de conhecimento (knowledge_base/)

- Os 5 CSVs formam um grafo de entidades: ver SDD §3 para esquema e contratos.
- **IDs são imutáveis** após atribuídos. Novos registros recebem o próximo ID na sequência.
- Toda edição de `fase2/knowledge_base/*.csv` **dispara automaticamente** os testes de contrato via hook PostToolUse.
- Depois de editar a base, regenerar o mapa derivado: `python fase2/src/gerar_mapa_conhecimento.py` (o hook acusa se esquecer).
- Expressão com adjetivo flexionado em quem relata ("estava sentado") exige a forma do outro gênero ("estava sentada") — contrato de paridade de gênero (SDD §3, regra 10).
- Mudança de associação, peso ou condição esperada no golden é decisão clínica: registrar justificativa e marcar como pendente de validação da Dra. Fernanda.
- Não adicionar colunas extras sem atualizar `test_base_conhecimento.py` e o SDD.

## 7. Harness de testes

```bash
# Rodar suite completa da Fase 2
cd fase2 && python -m pytest tests/ -v

# Só base de conhecimento
python -m pytest fase2/tests/test_base_conhecimento.py -v

# Só golden (extrator)
python -m pytest fase2/tests/test_extrator_golden.py -v
```

- `xfail_strict = true` (configurado em `pytest.ini`): se um teste marcado xfail começar a passar, vire erro — limpar o marcador.
- Limitações conhecidas documentadas em `fase2/tests/` com `@pytest.mark.xfail` + referência ao SDD §7.

## 8. Avaliação do classificador

- Gates mínimos (definidos em `fase2/config/metas_avaliacao.json`):
  - `recall_alto_risco ≥ 0.90` ← métrica primária (falso negativo em triagem = erro grave)
  - `acuracia ≥ 0.80`
- Cross-validation **apenas no conjunto treino**; conjunto teste só no relatório final.
- Usar skill `/avaliar-classificador` para gerar relatório padronizado.

## 9. Commits

Formato do commit:
```
tipo(escopo): mensagem curta em PT-BR

Corpo opcional explicando o porquê.
```

Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.  
Exemplos de escopo: `knowledge-base`, `extrator`, `classificador`, `harness`, `sdd`.

## 10. Skills disponíveis

| Slash command              | Descrição                                    |
|----------------------------|----------------------------------------------|
| `/validar-base-conhecimento` | Roda testes de contrato da base de conhecimento |
| `/avaliar-classificador`     | Executa harness de avaliação + relatório     |
| `/checklist-entrega`         | Checklist completo de entrega da Fase 2      |

---

*Última atualização: 2026-10-06 | Equipe Grupo S — FIAP*
