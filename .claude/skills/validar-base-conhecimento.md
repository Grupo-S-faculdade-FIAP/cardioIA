---
name: validar-base-conhecimento
description: Roda os testes de contrato da base de conhecimento (SDD §3) e reporta violações
---

# Validar Base de Conhecimento

Executa `fase2/tests/test_base_conhecimento.py` e interpreta os resultados.

## Passos

1. Rodar os testes de contrato:

```bash
cd fase2 && python -m pytest tests/test_base_conhecimento.py -v --tb=short
```

2. Interpretar a saída:
   - **PASSED** → contrato ok para aquela regra
   - **FAILED** → violação — ler a mensagem de erro e identificar qual CSV e qual regra (ex: R1 = colunas consistentes, R2 = IDs únicos, R3 = padrão de ID, R4 = integridade referencial, R5 = conceito com expressão, R6 = conceito com associação, R7 = toda fonte usada, R8 = expressão sem duplicata normalizada, R9 = campos obrigatórios não vazios)
   - **XFAIL** → limitação conhecida; não requer ação

3. Para cada FAILED, mostrar:
   - Qual arquivo CSV
   - Qual ID ou linha está com problema
   - Qual regra do SDD §3 foi violada
   - Sugestão de correção

4. Se tudo passar, confirmar: "✅ Base de conhecimento em conformidade com o SDD §3 — N testes passaram."
