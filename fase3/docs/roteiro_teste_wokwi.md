# CardioIA — Fase 3: roteiro de teste no Wokwi + Node-RED

> ⚠️ **AVISO CLÍNICO:** Este sistema é um protótipo acadêmico e **NÃO** substitui avaliação médica.
> Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).

Este roteiro valida o firmware (`fase3/esp32/`) no Wokwi, de ponta a ponta até o dashboard do Node-RED, e define as capturas de tela que ilustram o relatório. Pode ser seguido por uma pessoa da equipe ou entregue ao Claude Desktop (agente com navegador/tela) usando o prompt da seção abaixo.

## Antes de começar

1. **Código no Wokwi.** O projeto indicado é https://wokwi.com/projects/479773169716093953 (`cardioIAiot`). Em 2026-11-04, conferi os arquivos públicos: `diagram.json` e `libraries.txt` correspondem aos locais. O código-fonte aparece na aba `README.md`, com a mesma lógica do repositório e sem o wrapper local opcional de `wifi_config.h`. Porém, o projeto não contém um arquivo `sketch.ino`; ao iniciar a simulação, a compilação falha por falta de `setup()` e `loop()`. A página mostrou **Save** desabilitado e **Sign in**, então não foi possível corrigir o projeto publicado nesta sessão. Veja a captura 06 abaixo.
2. **Node-RED.** Importe `node_red/cardioia-fase3-flow.json`, clique em **Deploy** e confirme que http://localhost:1880/dashboard abre com o card "Sinais vitais simulados".
3. **Quem faz o quê.** Os cliques no botão em ritmo (300 a 700 ms entre cliques) precisam de uma pessoa: um agente leva segundos por ação. O restante (digitar comandos no Serial, ajustar sensores, ler telas) o agente consegue fazer.
4. **Layout das capturas.** Wokwi (com o Monitor Serial visível) na metade esquerda da tela e o dashboard em outra janela, na metade direita, para cada captura mostrar os dois.

## Prompt para o Claude Desktop

Anexe `sketch.ino`, `diagram.json`, `libraries.txt` e `cardioia-fase3-flow.json` e cole o texto abaixo.

````text
# Missão: validar o firmware da Fase 3 do CardioIA no Wokwi + Node-RED e coletar evidências

## 1. Contexto (leia antes de agir)
CardioIA é um protótipo acadêmico (FIAP) de monitoramento cardíaco IoT. Tudo é SIMULADO: não existe dado real de paciente e nada aqui é dispositivo médico.

Arquitetura:
  DHT22 + DS18B20 + MPU6050 + botão → ESP32 (Wokwi) → LED + buzzer (alerta LOCAL)
                                          └→ Wi-Fi "Wokwi-GUEST" → MQTT (broker.hivemq.com:1883, sem TLS, QoS 0) → Node-RED local (dashboard)
Tópico MQTT: cardioia/fiap/fase3/enzf-477362937220720641/sinais

Hardware no diagrama (ESP32 DevKit C v4):
- DHT22 (GPIO 15): temperatura e umidade do AMBIENTE (padrão 24 °C / 40 %).
- DS18B20 (GPIO 4, pull-up de 4,7 kΩ): temperatura CORPORAL simulada (inicia em 36,5 °C). Clicar no sensor abre um controle de temperatura (-55 a 125 °C).
- MPU6050 (I2C: SDA 21, SCL 22, endereço 0x68): movimento. Clicar no sensor abre controles de aceleração X/Y/Z (repouso = X 0, Y 0, Z 1 g) e rotação X/Y/Z (repouso = 0).
- Botão vermelho (GPIO 18): cada clique é um batimento. Também responde à tecla "b" com o foco no diagrama.
- LED vermelho (GPIO 26) e buzzer (GPIO 27): alerta local.

O que o firmware faz (para você saber o que esperar):
- Lê DHT22 e DS18B20 e monta uma leitura a cada 2 s; o MPU6050 é lido a cada 100 ms.
- BPM = 60000 / intervalo entre cliques (ms). Só vale entre 300 e 2000 ms (30 a 200 BPM); fora disso zera. Sem clique por 4 s o BPM expira e a leitura fica "bpm_valido": false.
- Movimento: há movimento se a aceleração variar mais de 0,05 g entre amostras ou o giro passar de 10 °/s (valor constante não conta). Estados: "aguardando" (ainda sem movimento desde o boot), "ativo", "parado" (15 s sem movimento DEPOIS de já ter havido algum) e "indisponivel". O alerta "sem movimento" só vale depois do primeiro movimento.
- Alertas locais (decididos no ESP32, mesmo offline): BPM válido > 120 → LED + buzzer; temperatura corporal > 38 °C → LED + buzzer; parado → só LED (sem buzzer). O buzzer dá um bipe de 150 ms por segundo. Cada mudança aparece no Serial como "[ALERTA-LOCAL] ATIVO: ..." ou "[ALERTA-LOCAL] Normalizado.".
- Toda leitura entra primeiro numa fila circular de 1.800 posições. O dispositivo INICIA OFFLINE (não publica até receber `o`).
- Comandos no Monitor Serial (maiúsculas ou minúsculas): `f` = simula queda (para de publicar, continua coletando e alertando); `o` = habilita o envio, conecta Wi-Fi + MQTT e esvazia a fila em ordem (até 10 por ciclo); `s` = status.
- JSON publicado: dispositivo, id, timestamp_ms, temperatura, umidade, temp_corporal, temp_corporal_valida, bpm, bpm_valido, movimento, aceleracao_g, alertas_locais (máscara de bits: 1 = BPM, 2 = febre, 4 = sem movimento).

Regras do dashboard (Node-RED), card "Sinais vitais simulados":
- Gráfico de linha: só plota BPM com bpm_valido=true (eixo 0–220).
- Gauge "Temperatura corporal (DS18B20)", escala 30–42 °C: AZUL até 35, VERDE de 35 a 37,5, AMARELO de 37,5 a 38, VERMELHO a partir de 38.
- Gauge "Temperatura ambiental (DHT22)", escala 0–50 °C: VERDE até 30, AMARELO de 30 a 38, VERMELHO a partir de 38.
- Texto "Movimento (MPU6050)": "Aguardando primeiro movimento", "Em movimento", "SEM MOVIMENTO (parado além do tempo limite)" ou "Sensor de movimento indisponível", seguido de "(|a| = x.xx g)".
- Texto "Alertas locais do dispositivo (Edge)": "Nenhum" ou lista com "BPM elevado", "Febre", "Sem movimento".
- Texto "Status do monitoramento" (regras do próprio dashboard): "ALERTA: " + lista separada por " | " na ordem "BPM simulado elevado", "Febre (temperatura corporal elevada)", "Sem movimento", "Temperatura ambiental elevada"; sem nenhum: "Monitoramento sem alertas ativos". Reavaliado a cada mensagem (~2 s).

## 2. Postura e regras
- Seja cético: o objetivo é descobrir o que NÃO funciona. Nunca marque "OK" sem ter visto a evidência na tela. Se não conseguiu verificar, escreva NÃO VERIFICADO e diga por quê.
- Não invente, não arredonde e não complete logs de memória. Transcreva exatamente o que viu; marque trechos ilegíveis como [ilegível].
- NÃO clique em Save, Fork, Share nem em Deploy do Node-RED. NÃO edite nada além de colar os 3 arquivos anexados no editor do Wokwi (a simulação roda com a edição não salva). No Node-RED você só OLHA.
- Nunca digite senhas nem faça login por mim. Se o Wokwi pedir login ou indicar que o projeto é de outra conta, pare e me avise.
- Não instale nada e não abra sites além dos citados aqui. Não use "#" (curinga) em nenhum assinante MQTT.
- Se um passo falhar, siga a tabela da seção 8; se travar por mais de 3 tentativas, pare e me descreva o estado exato.
- Áudio: você não consegue ouvir o buzzer. Verifique-o só pelo que a tela mostra (animação do componente, se houver) e pelo Serial; marque o som como NÃO VERIFICADO.
- Se não conseguir salvar imagens em arquivo, pare no ponto de captura e escreva "TIRE O PRINT AGORA: <nome>"; eu tiro e respondo "ok".
- Se você tiver ferramenta para ler o texto da página, use-a para transcrever o Monitor Serial com fidelidade; caso contrário, leia pela imagem e marque o que não ficou nítido.
- Mantenha um LOG de ações com o horário aproximado de cada passo.

## 3. Divisão de trabalho (importante)
Você leva alguns segundos por ação, então NÃO consegue clicar o botão a 300–700 ms de intervalo. Por isso:
- VOCÊ faz: abrir/colar código, rodar a simulação, digitar comandos no Serial (`s`, `o`, `f`), ajustar DS18B20/DHT22/MPU6050, ler telas, capturar, relatar.
- EU (humano) faço: todos os cliques no botão vermelho que dependem de ritmo. Quando precisar, escreva exatamente "AGORA, [instrução do ritmo e duração]" e comece a capturar telas em sequência (uma a cada 2–3 s). Eu clico até você escrever "pode parar". Escolha depois a captura em que o texto de alerta aparece.
- Ritmos: "ritmo médio" ≈ 1 clique a cada 700 ms (≈ 85 BPM); "ritmo rápido" ≈ 1 clique a cada 400 ms (≈ 150 BPM, deve disparar alerta); "ritmo lento" ≈ 1 clique a cada 2,5 s (deve invalidar o BPM).

## 4. Layout para as capturas
Wokwi (com o Monitor Serial visível) na metade esquerda da tela e o dashboard http://localhost:1880/dashboard em OUTRA janela do navegador na metade direita (Win+Seta esquerda / direita). Assim cada captura mostra o Serial, o circuito (LED aceso ou apagado) e o dashboard ao mesmo tempo. Se você só controla o navegador e não consegue deixar duas janelas lado a lado, use duas abas: capture o Wokwi e o dashboard em sequência, no mesmo instante, e anote o horário de cada captura. O editor do Node-RED (http://localhost:1880) fica numa aba à parte, só para a captura 10.

Nomes das capturas: 01-wokwi-circuito-completo, 02-wokwi-serial-offline-pendentes, 03-wokwi-alerta-local-offline, 04-wokwi-serial-sync-mqtt, 05-dashboard-sem-alerta, 06-dashboard-alerta-bpm, 07-dashboard-alerta-febre, 08-dashboard-sem-movimento, 09-dashboard-alertas-combinados, 10-nodered-editor-fluxo.

## 5. Pré-voo (confirme tudo antes de começar e reporte o resultado)
P1. http://localhost:1880/dashboard abre? O card se chama "Sinais vitais simulados" e tem DOIS gauges, o texto de movimento e o texto de alertas locais? (Se mostrar "Group 1" ou só um gauge, o fluxo ANTIGO está carregado: pare e me avise, preciso reimportar o JSON anexo.)
P2. No editor do Node-RED: a aba se chama "CardioIA Fase 3"? O nó MQTT mostra "connected"? Abra o gauge "CardioIA - Temp. Corporal" e confira os segmentos 30, 35, 37.5 e 38; abra o gauge "CardioIA - Temperatura" e confira 0, 30 e 38. Feche SEM alterar (Cancel).
P3. Wokwi: abra https://wokwi.com/projects/479773169716093953 e confira se o código já é o dos anexos: a primeira linha do Serial deve ser "CardioIA - Fase 3: Edge + MQTT" e o sketch deve ter as funções manterConexao e atualizarAlertasLocais (o código antigo tinha iniciarWiFi / verificarMQTT). Anote o dono do projeto e se há botão Save disponível. Se o código for o dos anexos, o Passo 1 é só conferência.

## 6. Roteiro de testes
Em cada passo registre Esperado × Observado.

### Passo 1 — Código e circuito no Wokwi
1. Se o projeto já tiver o código dos anexos (P3), só confira. Caso contrário, substitua o conteúdo de sketch.ino, diagram.json e libraries.txt pelos anexos (peça-me para copiar cada arquivo para a área de transferência; Ctrl+A, Ctrl+V). Confira que não ficou texto duplicado.
2. libraries.txt deve ter "DHT sensor library for ESPx", "PubSubClient", "OneWire" e "DallasTemperature". O diagrama deve carregar SEM mensagem de erro de conexão e mostrar: ESP32, DHT22, botão vermelho, DS18B20 com resistor, MPU6050, LED com resistor e buzzer, todos com fios ligados. Se alguma peça estiver sobreposta a outra, reporte (não mova nada).
3. Inicie a simulação. Em caso de erro de compilação (por exemplo, biblioteca não encontrada), copie a mensagem COMPLETA e pare.
4. Esperado no Serial: "CardioIA - Fase 3: Edge + MQTT", "DHT22 e simulador BPM iniciados.", "DS18B20 (temp. corporal): encontrado", "MPU6050 (movimento): encontrado", "Modo inicial: OFFLINE", "Comandos: F=offline | O=online | S=status". Nenhuma mensagem [WIFI] ou [MQTT] ainda. Se algum sensor aparecer como "NAO encontrado", reporte e vá à seção 8.
5. CAPTURA 01-wokwi-circuito-completo (o circuito inteiro, com o Serial legível).

### Passo 2 — Coleta offline e fila
1. Espere ≥ 14 s sem tocar em nada. Esperado, a cada 2 s: "------ NOVA LEITURA ------" com Temperatura 24.0 C, Umidade 40.0 %, "Temp. corporal: 36.5 C", "BPM simulado: indisponivel", "Movimento: aguardando (|a|=1.00 g)", "Alertas locais: nenhum", "Conexao: OFFLINE (envio indisponivel)" e "[EDGE] Leitura #N armazenada. Pendentes: N", com N crescendo 1, 2, 3... sem pulos. Confirme também que o LED está apagado.
2. Aguarde mais de 20 s ao todo SEM mexer no MPU6050. Esperado: o movimento continua "aguardando" e NÃO aparece alerta "sem movimento" (o alerta só vale depois do primeiro movimento).
3. Digite `S` (maiúsculo) + Enter. Esperado: "STATUS CARDIOIA", Conectividade OFFLINE, "Leituras pendentes: N", "Leituras descartadas: 0", "Temp. corporal: 36.5 C", "Movimento: aguardando", "Alertas locais: nenhum".
4. Testes de BPM (me chame para clicar):
   a. "AGORA, 1 clique único". Esperado: "[PULSO] Total: 1 | BPM: 0.0" e a próxima leitura mostra BPM "indisponivel".
   b. "AGORA, ritmo médio por ~8 s". Esperado: "[PULSO] Total: X | BPM: ~85" e a leitura com "BPM simulado: ~85". Sem alerta.
   c. "AGORA, 2 cliques com ~2,5 s de intervalo". Esperado: BPM 0.0 / indisponivel (intervalo > 2000 ms é rejeitado).
   d. Pare de clicar e espere ≥ 5 s. Esperado: a leitura volta a "BPM simulado: indisponivel" (expiração em 4 s).
5. CAPTURA 02-wokwi-serial-offline-pendentes.

### Passo 3 — Alerta local funcionando OFFLINE (o ponto principal do Edge)
O dispositivo ainda está offline (nenhum `o` foi enviado).
1. Clique no DS18B20 e ajuste a temperatura para 39 °C. Esperado em até ~2 s: "[ALERTA-LOCAL] ATIVO: febre", LED ACESO, "Temp. corporal: 39.0 C" e "Alertas locais: febre" nas leituras seguintes e no status (`s`). O buzzer deve dar bipes (som: NÃO VERIFICADO; veja se o componente anima).
2. CAPTURA 03-wokwi-alerta-local-offline (LED aceso + Serial com o alerta, tudo offline).
3. Limite: ajuste para 38.0 °C. Esperado: "[ALERTA-LOCAL] Normalizado." e LED apagado (o limiar é "> 38", não "≥"). Depois ajuste para 38.5 °C: o alerta volta. Anote.
4. Deixe em 39 °C para o próximo passo (o alerta vai viajar na fila).

### Passo 4 — Sincronização após reconexão
1. Antes de digitar `o`, deixe o dashboard http://localhost:1880/dashboard aberto na outra janela. Anote o último id pendente (N) e o horário.
2. Digite `o` + Enter. Esperado, nesta ordem: "[ONLINE] Transmissao MQTT habilitada.", "[SYNC] Iniciando envio dos dados pendentes...", "[WIFI] Tentando conectar...", "[MQTT] Tentando conectar ao broker...", "[MQTT] Conectado ao broker!", depois "[MQTT] Publicacao aceita: #1", "#2", ... até #N em ordem crescente e sem pulos, e por fim "[SYNC] Fila de publicacoes pendentes esvaziada." A conexão pode levar alguns segundos (nova tentativa a cada 5 s). Anote quanto tempo levou e se houve "[MQTT] Falha, codigo: ...".
3. Conferência: todos os ids de #1 a #N saíram, sem pulo nem repetição? Digite `s`: "Leituras pendentes: 0" (ou 1 se uma leitura nova acabou de entrar).
4. No dashboard: o gráfico só mostra pontos das leituras com BPM válido; as leituras reenviadas chegam juntas (horário de chegada, não de coleta: limitação documentada). Como a febre estava ativa nas leituras reenviadas, o gauge corporal deve ficar VERMELHO (~39 °C) e o texto de alertas locais deve mostrar "Febre". Anote.
5. CAPTURA 04-wokwi-serial-sync-mqtt (tela dividida: Serial com a conexão e as publicações em ordem + dashboard).
6. Teste de queda e retorno: digite `f` (esperado "[OFFLINE] Transmissao MQTT desabilitada; coleta continua."), espere ~12 s (o dashboard deve PARAR de atualizar, mas o alerta local e o LED continuam), digite `o` de novo e confira que as leituras do período offline saem em ordem, sem lacuna e sem id repetido.
7. Com o envio estável, uma leitura nova deve aparecer como "[EDGE] ... Pendentes: 1" seguida de "[MQTT] Publicacao aceita: #N" (fila volta a 0 a cada ciclo).
8. Volte o DS18B20 para 36.5 °C e confirme "[ALERTA-LOCAL] Normalizado." e LED apagado.

### Passo 5 — Dashboard e alertas (com o envio habilitado)
O texto de alerta é reavaliado a cada 2 s e o BPM expira 4 s após o último clique: capture durante os cliques, não depois.
1. Estado normal (DS18B20 em 36.5 °C, DHT22 em 24 °C, sem cliques, MPU6050 em repouso): gauge corporal VERDE (~36,5), gauge ambiental VERDE (~24), movimento "Aguardando primeiro movimento (|a| = 1.00 g)", alertas locais "Nenhum", status "Monitoramento sem alertas ativos". CAPTURA 05-dashboard-sem-alerta.
2. Alerta de BPM: "AGORA, ritmo rápido por ~15 s" e capture em sequência. Esperado: pontos acima de 120 no gráfico (~150), status "ALERTA: BPM simulado elevado", alertas locais "BPM elevado" e "[ALERTA-LOCAL] ATIVO: BPM elevado" no Serial. CAPTURA 06-dashboard-alerta-bpm (escolha a melhor). Depois de "pode parar", espere ~6 s: o alerta deve normalizar sozinho e o gráfico NÃO ganha pontos novos. Anote o tempo.
3. Faixas do gauge corporal: DS18B20 em 34 °C (AZUL), 36.5 (VERDE), 37.8 (AMARELO sem alerta), 39 (VERMELHO). Em 39 °C: status "ALERTA: Febre (temperatura corporal elevada)" e alertas locais "Febre". CAPTURA 07-dashboard-alerta-febre. Volte para 36.5 °C.
4. DHT22 NÃO é febre: clique no DHT22 e ajuste para 39 °C. Esperado: gauge AMBIENTAL vermelho e status "ALERTA: Temperatura ambiental elevada", mas SEM "Febre" e SEM LED aceso (alerta só do dashboard). Volte para 24 °C.
5. Movimento: clique no MPU6050 e defina rotação X = 50 °/s. Esperado em até ~2 s: leitura "Movimento: ativo", dashboard "Em movimento (|a| = ...)". Volte rotação X para 0 e aguarde 17 s SEM mexer em mais nada. Esperado: "[ALERTA-LOCAL] ATIVO: sem movimento", LED ACESO (sem buzzer), dashboard com texto "SEM MOVIMENTO (parado além do tempo limite)", alertas locais "Sem movimento" e status "ALERTA: Sem movimento". CAPTURA 08-dashboard-sem-movimento. Mexa de novo (ex.: rotação X = 50 e volte a 0): deve normalizar ("Em movimento") e reiniciar a contagem.
6. Alertas combinados: DS18B20 em 39 °C + MPU6050 parado depois de movimento + "AGORA, ritmo rápido". Esperado: status "ALERTA: BPM simulado elevado | Febre (temperatura corporal elevada) | Sem movimento" (nessa ordem) e alertas locais "BPM elevado | Febre | Sem movimento". CAPTURA 09-dashboard-alertas-combinados (se o BPM e o "parado" não coincidirem no tempo, tente de novo e reporte). Depois volte tudo ao normal.
7. Editor do Node-RED, aba do fluxo com o nó MQTT "connected" e a barra lateral de debug com mensagens recebidas: CAPTURA 10-nodered-editor-fluxo.
8. Na barra de debug, expanda uma mensagem do nó "debug 1" e transcreva o JSON completo. Confirme que os 12 campos existem e que, sem cliques recentes, bpm_valido é false.

### Passo 6 — Verificação independente do broker (opcional, recomendado)
Objetivo: separar "o ESP32 publicou" de "o Node-RED recebeu". Numa aba nova, abra https://www.hivemq.com/demos/websocket-client/ , conecte (padrões do site) e assine SOMENTE o tópico exato cardioia/fiap/fase3/enzf-477362937220720641/sinais (sem curingas). Com o envio habilitado, confirme que as mensagens chegam a cada ~2 s e batem com o Serial (mesmos ids). Depois desconecte e feche a aba. Se o site não carregar, marque NÃO VERIFICADO.

### Passo 7 — Fora do alcance (declare como NÃO VERIFICADO, sem tentar)
- Descarte por fila cheia (leva ~1 h de coleta com 1.800 posições).
- Persistência após reiniciar o ESP32 (a fila é RAM e se perde).
- Som do buzzer.

## 7. Tabela de afirmações da documentação a confirmar
Confirme cada uma como VERDADEIRO / FALSO / NÃO VERIFICADO, com a evidência (passo ou captura):
A1. O dispositivo inicia offline e não publica nada até receber `o`.
A2. DS18B20 e MPU6050 são encontrados no boot.
A3. Uma leitura é guardada a cada ~2 s e a fila cresce offline.
A4. `f`, `o` e `s` funcionam (maiúsculo e minúsculo).
A5. Ao sincronizar, as leituras saem em ordem e a fila zera.
A6. Um clique único ou intervalo > 2000 ms não gera BPM válido; o BPM expira em ~4 s.
A7. Cliques com < 500 ms de intervalo geram BPM > 120 (e ≥ 300 ms é aceito).
A8. O gráfico só plota BPM válido.
A9. Gauge ambiental: verde até 30 °C, amarelo de 30 a 38 °C, vermelho a partir de 38 °C.
A10. Gauge corporal: azul até 35, verde de 35 a 37,5, amarelo de 37,5 a 38, vermelho a partir de 38.
A11. Febre só alerta acima de 38 °C (38.0 não alerta) e só pelo DS18B20: o DHT22 a 39 °C não gera "Febre" nem LED.
A12. Em repouso desde o boot o movimento fica "aguardando" e NÃO alerta, mesmo após 15 s.
A13. Depois de movimento, 15 s parado gera alerta "sem movimento" (LED sem buzzer) e novo movimento normaliza.
A14. O alerta local (LED e Serial) funciona com o dispositivo offline.
A15. O LED acende em qualquer alerta local e apaga ao normalizar.
A16. Os textos e a ordem dos alertas do dashboard batem com a seção 1, incluindo a combinação com " | ".
A17. Os alertas somem sozinhos quando a condição acaba.
A18. O texto "Alertas locais do dispositivo (Edge)" no dashboard bate com o "[ALERTA-LOCAL]" do Serial.
A19. Leituras reenviadas aparecem no gráfico com o horário de chegada.
A20. A mensagem JSON tem os 12 campos descritos.

## 8. Se algo falhar
- Erro de compilação → copie a mensagem inteira, pare.
- "DS18B20 ... NAO encontrado" → confira no diagrama o fio DQ → GPIO 4 e o resistor de 4,7 kΩ entre DQ e 3V3; reporte o que viu.
- "MPU6050 ... NAO encontrado" → confira SDA → GPIO 21, SCL → GPIO 22 e alimentação; reporte.
- Serial sem "Modo inicial: OFFLINE" ou com texto diferente do esperado → o código colado pode não ser o anexo; reporte as primeiras 10 linhas do Serial.
- `o` não conecta após ~30 s → anote os códigos "[MQTT] Falha, codigo: X" (-2 = rede/broker inacessível) e tente `f` e `o` uma vez; se persistir, pare.
- Dashboard não atualiza mas o Serial mostra "Publicacao aceita" → verifique no editor se o nó MQTT está "connected" e use o Passo 6.
- Gauge ambiental vermelho em 24 °C ou card chamado "Group 1" → fluxo antigo no Node-RED; pare e me avise.
- Simulação parou sozinha → reinicie, anote quando e por quê.

## 9. Formato da entrega (responda nesta ordem)
1. VEREDITO em 3 linhas: o firmware do repositório funciona no Wokwi de ponta a ponta, com os novos sensores e alertas locais? Sim / Sim com ressalvas / Não, e por quê.
2. Pré-voo (P1 a P3) com o que viu.
3. Tabela por passo: Passo | Esperado | Observado | OK / NÃO OK / NÃO VERIFICADO.
4. Tabela A1–A20.
5. Texto COMPLETO do Monitor Serial dos Passos 2, 3 e 4 (copie sem resumir) e o JSON do Passo 5.8.
6. Lista dos prints (nomes da seção 4) e quais ainda faltam eu tirar.
7. Divergências e anomalias (erros, ids repetidos ou faltando, atrasos grandes, cores/textos diferentes, LED que não acendeu), cada uma com o passo onde ocorreu.
8. Dono do projeto Wokwi, se o Save estava disponível e se o código que estava lá ANTES era diferente do anexo.
9. O LOG de ações com horários.
````

## Depois do teste

1. Salve as novas capturas em `evidencias/` (conforme os nomes definidos na seção 4).
2. Preencha a linha "Execução ponta a ponta no Wokwi" da tabela de verificações de `relatorio_mqtt.md` com o resultado obtido.
3. Se alguma afirmação da tabela A1–A20 vier como FALSO, corrija o firmware ou a documentação (e, se alterar limiares, sincronize ambos: firmware e Node-RED).
4. Regenere os PDFs dos relatórios.

## Execução registrada em 2026-11-04

- **Wokwi, projeto do link (ID 479773169716093953), execução completa aprovada (32 de 32):** depois que o `sketch.ino` foi adicionado ao projeto, a simulação compilou e rodou em sessão anônima de navegador automatizado (35 % a 80 % da velocidade real), com o dashboard do Node-RED local. Verificados: boot do firmware (DS18B20 e MPU6050 encontrados, modo OFFLINE); coleta offline com ids 1 a N sem pulos; alerta local de febre com o DS18B20 em 39 °C (LED aceso, buzzer ativo) sem nada chegar ao dashboard; após `o`, Wi-Fi e broker conectados, publicações #1 em diante em ordem e `[SYNC] Fila de publicacoes pendentes esvaziada.`; dashboard com `ALERTA: Febre (temperatura corporal elevada)`; 14 cliques a cerca de 150 BPM registrados como pulsos, com alerta local de BPM elevado e o alerta de BPM no dashboard; MPU6050 girado e devolvido ao repouso, com `sem movimento` após 15 s no Serial e no dashboard; comandos `f` e `s`. Capturas `12` a `19`. **Não verificados:** o som do buzzer (só o indicador visual do simulador) e a captura do editor do Node-RED. A leitura vem sempre do ESP32 simulado; não há hardware físico.
- **Histórico:** antes dessa execução, o projeto do link não tinha `sketch.ino` (o código estava na aba `README.md`) e a compilação falhava com `setup()` e `loop()` indefinidos (captura `06`); o arquivo foi adicionado em 2026-11-04. Uma execução anterior no projeto `cardioiaiot` (ID 479766849694291969), com a mesma versão do firmware, está nas capturas `01` a `05`.
- **Node-RED + MQTT:** Node-RED 5.0.9 e Dashboard 2.0 1.33.0 foram iniciados em ambiente isolado na porta 1881. O nó MQTT conectou ao broker público. Publiquei somente uma mensagem de teste sintética no tópico do projeto (ID 99004, BPM 130, temperaturas 39 °C, movimento `parado`, máscara 7); o dashboard atualizou os gauges, movimento, alertas locais e status Fog esperados. Isso valida o consumidor MQTT/dashboard, mas não substitui a publicação do ESP32 simulado no Wokwi (a execução acima).
- **Capturas** em `evidencias/validacao-2026-11-04/`: `12` a `19` (execução final no Wokwi e dashboard), `01` a `05` (execução anterior), `06` (falha de build anterior), `07` e `08` (dashboard com mensagem sintética, que não vem do Wokwi) e `09` (86 testes locais aprovados).
