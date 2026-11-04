# Node-RED — camada Fog do CardioIA (Fase 3)

> ⚠️ **AVISO CLÍNICO:** Este sistema é um protótipo acadêmico e **NÃO** substitui avaliação médica.
> Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).

Esta pasta é um projeto **autônomo**: o fluxo do dashboard, as instruções para rodá-lo e os testes que o protegem. Ele não compartilha código com o firmware do ESP32; a **única ligação** entre os dois é o [contrato MQTT](../docs/contrato_mqtt.md) (tópico, campos da mensagem e limiares de alerta). Todos os dados são simulados; nenhum dado de paciente.

```text
ESP32 (Wokwi) ──MQTT──► broker.hivemq.com ──► Node-RED (este fluxo) ──► Dashboard 2.0
     Edge                 tópico do contrato           Fog
```

## O que tem aqui

```text
node_red/
├── cardioia-fase3-flow.json   fluxo e dashboard exportados: a fonte da verdade
├── package.json               só os scripts de teste (nenhuma dependência para instalar)
├── README.md                  este arquivo
└── tests/
    ├── utilitarios.mjs        lê firmware, fluxo e contrato; executa os nós "function"
    ├── funcoes.test.mjs       regras de cada nó, inclusive os limites exatos
    └── contrato.test.mjs      firmware × fluxo × contrato × READMEs e relatórios
```

## Versões testadas

| Componente | Versão |
|---|---|
| Node.js | 20 ou superior (testado com 25.8.1) |
| Node-RED | 5.0.9 |
| Dashboard 2.0 (`@flowfuse/node-red-dashboard`) | 1.33.0 |

## Conexão MQTT

| Item | Valor |
|---|---|
| Broker | `broker.hivemq.com`, porta `1883`, sem TLS e sem autenticação |
| Tópico | `cardioia/fiap/fase3/enzf-477362937220720641/sinais` |

A mensagem tem 12 campos em JSON; todos estão descritos no [contrato](../docs/contrato_mqtt.md).

## Como rodar o dashboard

1. Instale o Node-RED: `npm install -g node-red@5.0.9`.
2. Rode `node-red` uma vez para ele criar a pasta de usuário (`~/.node-red`; no Windows, `C:\Users\<você>\.node-red`) e encerre com Ctrl+C.
3. Instale o dashboard **na versão do fluxo**, dentro dessa pasta:

   ```bash
   cd ~/.node-red               # Windows (PowerShell): cd $env:USERPROFILE\.node-red
   npm install @flowfuse/node-red-dashboard@1.33.0
   ```

4. Restrinja o editor à sua máquina (veja "Segurança" abaixo) e inicie `node-red`.
5. No editor (http://localhost:1880): menu ☰ → **Import** → escolha `cardioia-fase3-flow.json` → **Import** → **Deploy**.
6. Confira que o nó `mqtt in` mostra **connected** (ponto verde). Ele conecta no broker HiveMQ, então precisa de internet.
7. Abra http://localhost:1880/dashboard. Com o Wokwi rodando e o envio habilitado (`o` no Monitor Serial), os dados aparecem.

Alternativa sem o editor: com o Node-RED parado, copie `cardioia-fase3-flow.json` para `~/.node-red/flows.json` e inicie o Node-RED.

## Segurança

- **O editor do Node-RED não tem senha e executa código.** Por padrão ele escuta em todas as interfaces de rede. Em `~/.node-red/settings.js`, defina `uiHost: "127.0.0.1",` para aceitar só a sua máquina (o dashboard continua em `localhost`).
- **O broker é público e sem criptografia:** qualquer pessoa que souber o tópico consegue ler e publicar. Nunca envie dados reais.
- O fluxo não guarda usuário, senha nem token (os testes conferem isso).

## O que o fluxo faz

Um nó `mqtt in` recebe cada mensagem e a entrega a seis funções independentes, cada uma ligada a um widget:

| Nó | Campos que lê | Widget no dashboard |
|---|---|---|
| Processar BPM | `bpm`, `bpm_valido` | gráfico de linha (só leituras válidas) |
| Processar Temperatura | `temperatura` | gauge da temperatura ambiental (0 a 50 °C) |
| Processar Temp. Corporal | `temp_corporal`, `temp_corporal_valida` | gauge da temperatura corporal (30 a 42 °C) |
| Processar Movimento | `movimento`, `aceleracao_g` | texto "Movimento (MPU6050)" |
| Processar Alertas Locais | `alertas_locais` | texto "Alertas locais do dispositivo (Edge)" |
| Verificar Alertas | `bpm`, `bpm_valido`, `temp_corporal`, `temp_corporal_valida`, `movimento`, `temperatura` | texto "Status do monitoramento" |

Mensagens que não são um objeto JSON são descartadas sem erro. As regras de alerta e seus limites estão no [contrato](../docs/contrato_mqtt.md#limiares-e-regras-de-alerta).

## Testes

| Comando | O que confere | Requisitos |
|---|---|---|
| `npm test` | regras de cada nó + contrato (firmware × fluxo × documentos) | só Node.js 20+; não instala nada; roda em segundos |

Execute `npm test` dentro de `fase3/node_red`. A integração real Wokwi → broker → Node-RED não tem teste automatizado neste repositório; siga o [roteiro manual](../docs/roteiro_teste_wokwi.md) e registre as evidências da versão atual.

## Alterando o fluxo com segurança

1. Edite no editor do Node-RED e clique em **Deploy**.
2. Menu ☰ → **Export** → **all flows** → baixe o JSON e salve **por cima** de `cardioia-fase3-flow.json`. O `flows.json` da sua pasta de usuário é só uma cópia; o repositório é a fonte da verdade.
3. Rode `npm test`. Se mudou campo, tópico ou limiar, atualize antes o [contrato](../docs/contrato_mqtt.md), o firmware (e o projeto no Wokwi), o [README da Fase 3](../README.md) e os relatórios; o teste aponta o que ficou para trás.
4. Se o fluxo ou o contrato mudaram, regenere os PDFs dos relatórios e refaça as evidências afetadas.

## Por que esta pasta fica no mesmo repositório

- **Mudanças atômicas:** o contrato exige que firmware, fluxo e documentos mudem juntos (limiares de BPM e febre existem nos dois lados). Num único repositório isso é um commit e um PR; em dois seria uma coordenação manual entre repositórios, com risco de divergência.
- **Entrega única:** a avaliação da Fase 3 usa um só repositório, com firmware, fluxo, relatórios e evidências lado a lado.
- **O acoplamento é só por contrato:** nenhum código é compartilhado e os testes checam o contrato nos dois lados. Se o fluxo passar a ser reaproveitado por outro serviço, dá para extraí-lo com o histórico: `git subtree split --prefix=fase3/node_red`.

## Limitações conhecidas

- O dashboard mostra a **última** mensagem recebida: se o ESP32 ficar offline, os valores antigos continuam na tela. Não há alerta de "sem dados".
- O gráfico plota cada leitura no horário em que ela **chegou**, não no da coleta (o `timestamp_ms` é relativo ao boot do ESP32). Leituras reenviadas após uma reconexão aparecem juntas.
- QoS 0: sem confirmação de entrega ponta a ponta.
- Os limiares são regras demonstrativas, não critérios de diagnóstico.
