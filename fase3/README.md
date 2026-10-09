# CardioIA — Fase 3

## Monitoramento Contínuo — IoT na Saúde

A Fase 3 do CardioIA tem como objetivo desenvolver um protótipo de monitoramento contínuo de sinais vitais, utilizando IoT, Edge Computing, comunicação MQTT e dashboards interativos.

O sistema simula um dispositivo de monitoramento cardíaco capaz de coletar dados, armazenar temporariamente informações durante falhas de conectividade e sincronizá-las quando a conexão é restabelecida.

## Projeto no Wokwi

**Simulação:** https://wokwi.com/projects/477362937220720641

### Componentes utilizados

| Componente | Função |
|---|---|
| ESP32 | Processamento e controle das leituras |
| DHT22 | Medição simulada de temperatura e umidade |
| Pushbutton | Simulação manual de pulsos cardíacos |

### Conexões

- DHT22: VCC → 3V3, SDA → GPIO 15, GND → GND.
- Pushbutton: terminal `2.l` → GPIO 18; terminal `1.r` → GND.

## Parte 1 — Edge Computing

**Status: implementação funcional no Wokwi.**

O sistema realiza:

- Leitura de temperatura e umidade a cada dois segundos.
- Detecção de pulsos simulados através do botão.
- Estimativa de BPM baseada no intervalo entre acionamentos.
- Simulação de estados online e offline.
- Armazenamento temporário em fila circular.
- Sincronização das leituras pendentes após reconexão.
- Exibição das operações no Monitor Serial.

### Resiliência offline

A fila circular possui capacidade para **1.800 leituras**, equivalente a aproximadamente uma hora de coleta a cada dois segundos.

Quando a conexão simulada está indisponível, as leituras continuam sendo coletadas e armazenadas na memória do ESP32.

Ao restaurar a conexão, os registros pendentes são transmitidos sequencialmente, preservando a ordem de coleta.

Se a fila atingir sua capacidade máxima, a leitura mais antiga é descartada e o evento é contabilizado.

### Comandos do Monitor Serial

| Comando | Ação |
|---|---|
| `f` | Simular perda de conexão |
| `o` | Restaurar conexão |
| `s` | Consultar status |

### Limitações

O armazenamento utilizado é volátil e não persiste após o encerramento da simulação.

O BPM representa uma estimativa baseada em acionamentos manuais, não uma medição fisiológica real.

A transmissão da Parte 1 é simulada por mensagens no Monitor Serial. O envio real através de MQTT será implementado na Parte 2.

## Como executar

1. Acesse o projeto no Wokwi.
2. Inicie a simulação.
3. Pressione o botão para simular pulsos.
4. Observe temperatura, umidade e BPM no Monitor Serial.
5. Mantenha o dispositivo offline para acumular leituras.
6. Envie o comando `o` no terminal para simular a reconexão.
7. Observe a sincronização dos registros pendentes.

## Estrutura

```text
fase3/
├── esp32/
│   ├── sketch.ino
│   ├── diagram.json
│   └── libraries.txt
├── docs/
│   └── evidencias/
└── README.md
```

## Parte 2 — Fog/Cloud Computing

**Status: pendente.**

Próximas implementações:

- Publicação de dados utilizando MQTT.
- Integração com broker MQTT.
- Recebimento das mensagens no Node-RED.
- Dashboard com gráfico de sinais vitais.
- Medidor de temperatura.
- Alertas automáticos.

## Aviso

Este projeto é um protótipo acadêmico desenvolvido com sensores simulados. Não constitui dispositivo médico validado nem deve ser utilizado para diagnóstico ou monitoramento clínico real.


## Arquitetura da solução

O protótipo utiliza um ESP32 simulado no Wokwi, integrado
a um broker MQTT público e a um dashboard Node-RED.

Fluxo de comunicação:

ESP32 (Wokwi)
    |
    | Wi-Fi / MQTT
    v
HiveMQ Public Broker
    |
    v
Node-RED
    |
    +-- Gráfico de BPM simulado
    +-- Medidor de temperatura ambiental
    +-- Alertas automáticos

## Sensores simulados

- DHT22: temperatura e umidade ambiental.
- Pushbutton: simulação manual de pulsos cardíacos.

O BPM é uma estimativa demonstrativa calculada a partir
dos intervalos entre os acionamentos do botão.

## Comunicação MQTT

Broker: broker.hivemq.com

Porta: 1883

Tópico:
cardioia/fiap/fase3/enzf-477362937220720641/sinais

O broker é público e não utiliza autenticação ou
criptografia nesta configuração. Não devem ser enviados
dados pessoais ou clínicos reais.

## Resiliência offline

O ESP32 mantém uma fila circular com capacidade para
1.800 leituras.

Comandos disponíveis no Monitor Serial:

- f: desabilita a transmissão MQTT.
- o: habilita a transmissão e tenta sincronizar a fila.
- s: exibe o status do dispositivo.

A fila é mantida em memória RAM e não persiste após
reinicialização do ESP32.

## Dashboard Node-RED

O fluxo exportado está disponível em:

node_red/cardioia-fase3-flow.json

Para reproduzir:

1. Instale o Node-RED.
2. Instale @flowfuse/node-red-dashboard.
3. Importe o arquivo JSON no editor Node-RED.
4. Configure e conecte o broker MQTT, se necessário.
5. Faça Deploy.
6. Acesse http://localhost:1880/dashboard.

## Documentação técnica

- docs/relatorio_edge.md
- docs/relatorio_mqtt.md

## Observações

Este projeto é um protótipo acadêmico.

O DHT22 mede temperatura ambiental, não corporal.
O BPM é simulado e não representa uma medição clínica.

A publicação MQTT utiliza QoS 0, sem garantia de
entrega de ponta a ponta.