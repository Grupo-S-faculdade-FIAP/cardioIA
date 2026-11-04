# Contrato MQTT — CardioIA Fase 3

> ⚠️ **AVISO CLÍNICO:** Este sistema é um protótipo acadêmico e **NÃO** substitui avaliação médica.
> Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).

**Versão do contrato:** 1.0 (2026-11-04) · **Produtor:** firmware do ESP32 ([`esp32/sketch.ino`](../esp32/sketch.ino)) · **Consumidor:** fluxo Node-RED ([`node_red/cardioia-fase3-flow.json`](../node_red/cardioia-fase3-flow.json))

O firmware e o fluxo Node-RED não compartilham código: a **única ligação** entre eles é uma mensagem MQTT. Este documento é a fonte única do que essa mensagem contém e das regras de alerta aplicadas dos dois lados. A mensagem não carrega número de versão; a versão do contrato vive só aqui.

As tabelas abaixo são **lidas pelos testes** de [`node_red/tests/contrato.test.mjs`](../node_red/tests/contrato.test.mjs). Se o firmware, o fluxo, este documento ou os exemplos dos READMEs divergirem, `npm test` (em `fase3/node_red`) falha e aponta onde. Por isso as tabelas seguem um formato fixo: não renomeie títulos nem colunas sem ajustar o teste.

Todos os dados são simulados; nenhum dado de paciente trafega por este contrato.

## Transporte

| Item | Valor |
|---|---|
| Broker | `broker.hivemq.com` |
| Porta | `1883` |
| Tópico | `cardioia/fiap/fase3/enzf-477362937220720641/sinais` |
| QoS | `0` |
| Retain | `não` |
| Criptografia e autenticação | nenhuma (broker público: somente dados fictícios) |
| Identificador do cliente (ESP32) | `cardioia-esp32-enzf-477362937220720641` |
| Cadência | uma mensagem por leitura; coleta a cada 2 s; ao reconectar, até 10 leituras da fila por passagem do `loop()`, em ordem de coleta |

QoS 0 e retain desligado são o comportamento padrão de `mqtt.publish(topico, payload)` na biblioteca PubSubClient, usado pelo firmware.

## Campos do payload

Mensagem em JSON, uma por leitura, com os 12 campos abaixo **nesta ordem** (a ordem é a do `snprintf` do firmware). O consumidor deve ignorar campos desconhecidos e tratar campo ausente como leitura inválida (caso do formato antigo, anterior ao DS18B20 e ao MPU6050).

| Campo | Tipo | Valores e unidade | Origem | Nós do Node-RED que usam |
|---|---|---|---|---|
| `dispositivo` | texto | fixo `cardioia-esp32-01` | firmware | — |
| `id` | inteiro | sequencial a partir de 1, um por leitura | fila Edge | — |
| `timestamp_ms` | inteiro | `millis()` do ESP32 desde o boot, em ms (não é horário civil) | ESP32 | — |
| `temperatura` | número | °C, 1 casa; temperatura do **ambiente** | DHT22 | Processar Temperatura; Verificar Alertas |
| `umidade` | número | %, 1 casa | DHT22 | — |
| `temp_corporal` | número | °C, 1 casa; `0.0` quando `temp_corporal_valida` é `false` | DS18B20 | Processar Temp. Corporal; Verificar Alertas |
| `temp_corporal_valida` | booleano | `false`: ignorar `temp_corporal` | DS18B20 | Processar Temp. Corporal; Verificar Alertas |
| `bpm` | número | batimentos por minuto, 1 casa; `0.0` sem estimativa | botão | Processar BPM; Verificar Alertas |
| `bpm_valido` | booleano | `false`: ignorar `bpm` | botão | Processar BPM; Verificar Alertas |
| `movimento` | texto | um dos estados da tabela de movimento | MPU6050 | Processar Movimento; Verificar Alertas |
| `aceleracao_g` | número | módulo da aceleração em g, 2 casas (cerca de 1,00 em repouso); `0.00` se o MPU6050 estiver ausente | MPU6050 | Processar Movimento |
| `alertas_locais` | inteiro | máscara de bits da tabela de alertas locais | ESP32 | Processar Alertas Locais |

Exemplo (leitura em repouso, sem alertas):

```json
{
  "dispositivo": "cardioia-esp32-01",
  "id": 9,
  "timestamp_ms": 18000,
  "temperatura": 24.0,
  "umidade": 40.0,
  "temp_corporal": 36.5,
  "temp_corporal_valida": true,
  "bpm": 0.0,
  "bpm_valido": false,
  "movimento": "aguardando",
  "aceleracao_g": 1.00,
  "alertas_locais": 0
}
```

## Alertas locais (máscara)

O ESP32 avalia os alertas no próprio dispositivo (LED e buzzer, mesmo offline) e envia o conjunto no campo `alertas_locais`, como soma de bits.

| Bit | Valor | Alerta | Constante no firmware | Texto no dashboard |
|---|---|---|---|---|
| 0 | 1 | BPM elevado | `ALERTA_BPM` | BPM elevado |
| 1 | 2 | Febre | `ALERTA_FEBRE` | Febre |
| 2 | 4 | Sem movimento | `ALERTA_SEM_MOVIMENTO` | Sem movimento |

Exemplos: `0` = nenhum alerta; `3` = BPM elevado e febre; `7` = os três. Bits fora desta tabela são ignorados pelo consumidor.

## Estados de movimento

| Estado | Significado | Texto no dashboard |
|---|---|---|
| `aguardando` | ainda não houve movimento desde o boot; o alerta de "sem movimento" fica desarmado | Aguardando primeiro movimento |
| `ativo` | houve movimento nos últimos 15 s | Em movimento |
| `parado` | sem movimento há 15 s ou mais, depois de já ter havido movimento | SEM MOVIMENTO (parado além do tempo limite) |
| `indisponivel` | o MPU6050 não responde | Sensor de movimento indisponível |

Quando `aceleracao_g` é numérico e o estado não é `indisponivel`, o dashboard acrescenta o módulo da aceleração ao texto, no formato `(|a| = 1.00 g)`.

## Limiares e regras de alerta

Valores demonstrativos, **não** são critérios de diagnóstico. Todas as comparações são "maior que" (o valor exato do limite **não** alerta).

| Regra | Condição | Valor | Constante no firmware | Onde o Node-RED aplica | Texto do alerta no dashboard |
|---|---|---|---|---|---|
| BPM elevado | `bpm_valido` e `bpm` maiores que o valor | 120 | `LIMITE_BPM` | Verificar Alertas | BPM simulado elevado |
| Febre | `temp_corporal_valida` e `temp_corporal` maiores que o valor (DS18B20) | 38 | `LIMITE_FEBRE` | Verificar Alertas | Febre (temperatura corporal elevada) |
| Sem movimento | `movimento` igual a `parado`, estado decidido no ESP32 após 15000 ms sem movimento | 15000 | `TEMPO_SEM_MOVIMENTO_MS` | Verificar Alertas (só repassa o estado `parado`) | Sem movimento |
| Temperatura ambiental elevada | `temperatura` maior que o valor (DHT22; **não** indica febre) | 38 | — | Verificar Alertas | Temperatura ambiental elevada |

Onde cada regra mora:

- **BPM e febre** existem nos dois lados (firmware e Node-RED) e precisam coincidir.
- **Temperatura ambiental** existe só no Node-RED: o firmware não tem alerta local para ela.
- **Sem movimento** é decidido só no firmware (os 15000 ms); o Node-RED apenas repassa o estado `parado`.

No dashboard, alertas simultâneos aparecem na ordem da tabela, separados por ` | ` e precedidos de `ALERTA: `. Sem nenhum, o texto é `Monitoramento sem alertas ativos`.

## Compatibilidade

- **Campos desconhecidos:** o consumidor os ignora, então acrescentar um campo ao final não quebra o dashboard.
- **Mensagem que não é um objeto JSON** (texto solto, número, JSON quebrado): descartada sem erro e sem alterar o dashboard.
- **Formato antigo** (somente `temperatura`, `umidade`, `bpm` e `bpm_valido`): continua sendo processado; os campos novos ausentes não geram alerta nem erro.

## Como alterar o contrato

1. Edite o firmware ([`sketch.ino`](../esp32/sketch.ino)) **e copie a mudança para o projeto no Wokwi**, edite o fluxo no Node-RED e exporte-o por cima de `cardioia-fase3-flow.json`, e atualize as tabelas deste documento.
2. Rode `npm test` em `fase3/node_red` e corrija o que os testes apontarem.
3. Atualize o exemplo de payload e as tabelas de [`README.md`](../README.md) e dos relatórios ([`relatorio_edge.md`](relatorio_edge.md), [`relatorio_mqtt.md`](relatorio_mqtt.md)).
4. Siga o teste integrado manual em [`roteiro_teste_wokwi.md`](roteiro_teste_wokwi.md) e refaça as evidências afetadas.
5. Regenere os PDFs dos relatórios.

## O que os testes conferem

| Conferência | Onde |
|---|---|
| Broker, porta, tópico, QoS e retain: firmware × fluxo × tabela de transporte | `contrato.test.mjs` |
| Campos, ordem e tipos: `snprintf` do firmware × tabela × exemplos dos READMEs | `contrato.test.mjs` |
| Campos que cada nó lê: código do fluxo × coluna "Nós do Node-RED que usam" | `contrato.test.mjs` |
| Máscara de bits, estados de movimento e limiares: firmware × fluxo × tabelas, inclusive o comportamento nos valores-limite | `contrato.test.mjs` |
| Regras de cada nó (limites exatos, leituras inválidas, formato antigo, máscara) e concordância entre as regras do Edge e do Fog | `funcoes.test.mjs` |
| Integridade do fluxo (ids, fios, referências), ausência de credenciais e texto de alerta sem corte | `contrato.test.mjs` |

O teste integrado Wokwi → broker → Node-RED é manual e está descrito em [`roteiro_teste_wokwi.md`](roteiro_teste_wokwi.md); ainda não há teste automatizado ponta a ponta.
## Limitações

- **QoS 0:** sem confirmação de entrega ponta a ponta; uma mensagem pode se perder sem aviso.
- **`timestamp_ms` relativo ao boot:** leituras reenviadas após a reconexão aparecem no gráfico no horário de chegada, não no de coleta.
- **Broker público e sem TLS:** só serve para dados fictícios. Em produção seriam necessários TLS, autenticação e controle de acesso por tópico.
- **Sem versão na mensagem:** uma mudança incompatível exige atualizar produtor e consumidor juntos.
