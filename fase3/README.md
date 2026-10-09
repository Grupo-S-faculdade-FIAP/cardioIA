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