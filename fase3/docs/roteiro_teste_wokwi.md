# CardioIA — Fase 3: roteiro de teste no Wokwi + Node-RED

> ⚠️ **AVISO CLÍNICO:** Este sistema é um protótipo acadêmico e **NÃO** substitui avaliação médica.
> Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).

Este roteiro valida o firmware (`fase3/esp32/`) no Wokwi, de ponta a ponta até o dashboard do Node-RED, e define as capturas que ilustram os relatórios. Tudo é simulado: não há hardware físico nem dado de paciente.

## Antes de começar

1. **Projeto no Wokwi:** https://wokwi.com/projects/479773169716093953 (`cardioIAiot`). Ele deve ter `sketch.ino`, `diagram.json` e `libraries.txt` iguais aos de [`esp32/`](../esp32/). Cole o `sketch.ino` inteiro do repositório no projeto: o bloco opcional de Wi-Fi (`#if __has_include("wifi_config.h")`) não faz nada no Wokwi, que não tem esse arquivo, e vale o padrão `Wokwi-GUEST`; o comportamento na simulação é o mesmo. O projeto do link já tem o `sketch.ino` atual (salvo pelo dono da conta; conferido por diff em 2026-11-04). A execução final foi feita um pouco antes, com o mesmo arquivo colado no editor sem salvar, e as capturas 12 a 22 são dessa execução. O arquivo compila e roda no Wokwi com o padrão `Wokwi-GUEST`. Se mudar um lado, copie a mudança para o outro: só o dono da conta consegue salvar no Wokwi.
2. **Node-RED:** siga o [README do Node-RED](../node_red/README.md), faça o **Deploy** do fluxo e confirme que http://localhost:1880/dashboard abre com o card "Sinais vitais simulados" (dois gauges, texto de movimento e texto de alertas locais). Se aparecer "Group 1" ou só um gauge, é o fluxo antigo: reimporte [`cardioia-fase3-flow.json`](../node_red/cardioia-fase3-flow.json).
3. **Quem clica:** os cliques no botão em ritmo (300 a 500 ms entre cliques) pedem uma pessoa, ou um script que conte o tempo pelo relógio da simulação.
4. **Tela:** o Wokwi com o Monitor Serial visível numa metade e o dashboard em outra janela, na outra metade, para cada captura mostrar Serial, circuito (LED) e dashboard.

## O que esperar (referência)

- **Controles no simulador:** clique no DS18B20 (temperatura corporal, inicia em 36,5 °C), no DHT22 (ambiente, 24 °C) e no MPU6050 (aceleração X/Y/Z, repouso = 0, 0, 1 g; rotação X/Y/Z, repouso = 0). O botão vermelho (GPIO 18) é o batimento e também responde à tecla `b`.
- **BPM:** 60000 dividido pelo intervalo entre cliques em ms, válido de 300 a 2000 ms. Sem clique por 4 s, o BPM expira.
- **Movimento:** há movimento se a aceleração variar mais de 0,05 g entre amostras ou o giro passar de 10 °/s. Estados: `aguardando`, `ativo`, `parado` (15 s sem movimento depois de já ter havido algum) e `indisponivel`. O alerta só vale depois do primeiro movimento.
- **Alertas locais** (decididos no ESP32, mesmo offline): BPM válido acima de 120 e temperatura corporal acima de 38 °C acendem LED e buzzer; "parado" acende só o LED. No Serial: `[ALERTA-LOCAL] ATIVO: ...` e `[ALERTA-LOCAL] Normalizado.`.
- **Comandos no Serial** (maiúsculas ou minúsculas): `f` simula a queda da rede, `o` habilita o envio e esvazia a fila em ordem, `s` mostra o status. O dispositivo **inicia offline**.
- **Dashboard:** o status junta os alertas com ` | ` depois de `ALERTA: `, sempre na ordem BPM, febre, sem movimento e temperatura ambiental; sem alerta, mostra `Monitoramento sem alertas ativos`. Campos, textos e limiares: [contrato MQTT](contrato_mqtt.md).
- **Banner e watchdog:** o banner no topo do painel mostra `ALERTA` (vermelho), `SEM DADOS` (laranja), `SEM ALERTAS` (verde) ou `AGUARDANDO DADOS` (cinza, antes da primeira leitura). Se nenhuma leitura chegar por 30 s (por exemplo, depois do comando `f`), o status e o banner passam a `SEM DADOS: …`; a leitura seguinte restaura o estado. O aviso clínico fica no rodapé do painel.

## Roteiro

### 1. Circuito e boot

1. Confira o circuito (ESP32, DHT22, botão, DS18B20 com resistor, MPU6050, LED com resistor e buzzer, tudo ligado) e inicie a simulação. Se a compilação falhar, copie a mensagem completa.
2. Serial esperado: `CardioIA - Fase 3: Edge + MQTT`, `DS18B20 (temp. corporal): encontrado`, `MPU6050 (movimento): encontrado`, `Modo inicial: OFFLINE` e `Comandos: F=offline | O=online | S=status`, sem nenhuma linha `[WIFI]` ou `[MQTT]`. **Captura 12.**

### 2. Coleta offline

1. Espere 14 s. A cada 2 s deve aparecer uma leitura com `Temp. corporal: 36.5 C`, `BPM simulado: indisponivel`, `Movimento: aguardando`, `Alertas locais: nenhum`, `Conexao: OFFLINE` e `[EDGE] Leitura #N armazenada. Pendentes: N`, com N subindo de 1 em 1. O LED fica apagado. A leitura nº 1 pode mostrar a temperatura corporal como indisponível, porque o DS18B20 ainda está na primeira conversão.
2. Sem mexer no MPU6050 por mais de 20 s, o movimento continua `aguardando` e **não** há alerta de sem movimento.
3. Digite `s`: `STATUS CARDIOIA`, `Leituras pendentes: N` e `Leituras descartadas: 0`.

### 3. Alerta local offline

1. Clique no DS18B20 e leve a temperatura a 39 °C. Em cerca de 2 s: `[ALERTA-LOCAL] ATIVO: febre`, LED aceso, indicador de som no buzzer e `Alertas locais: febre`. O dashboard **não** recebe nada, porque o dispositivo está offline. **Captura 13.**
2. Limite: com 38,0 °C o alerta normaliza (o limiar é "maior que 38"); com 38,5 °C ele volta. Deixe em 39 °C.

### 4. Sincronização

1. Com o dashboard aberto, digite `o`. Esperado, nesta ordem: `[ONLINE] Transmissao MQTT habilitada.`, `[SYNC] Iniciando envio dos dados pendentes...`, `[WIFI] Tentando conectar...`, `[MQTT] Conectado ao broker!`, `[MQTT] Publicacao aceita: #1 | amb 24.0 C | corpo 36.5 C | BPM indisponivel` (a linha traz um resumo do dado enviado), `#2` e assim por diante, em ordem, sem pulo nem repetição, até `[SYNC] Fila de publicacoes pendentes esvaziada.` A conexão pode levar alguns segundos. **Captura 14.**
2. No dashboard: gauge corporal vermelho (cerca de 39 °C), ambiental em 24 °C, `Alertas locais: Febre` e `ALERTA: Febre (temperatura corporal elevada)`. As leituras reenviadas chegam juntas e o gráfico as plota no horário de chegada (limitação documentada). **Captura 17.**
3. Digite `f`: `[OFFLINE] Transmissao MQTT desabilitada; coleta continua.` O dashboard para de atualizar, mas a coleta e o LED continuam. Depois de 30 s sem leituras, o status e o banner passam a `SEM DADOS: …` (watchdog); é o momento de capturar o banner laranja (sugestão: captura `21`). Digite `o` de novo: as leituras do período offline saem em ordem e o banner volta ao normal.

### 5. Alertas no dashboard (com o envio habilitado)

O BPM expira 4 s depois do último clique e o status é reavaliado a cada mensagem (cerca de 2 s): capture **durante** os cliques.

1. **BPM:** cliques a cerca de 400 ms de intervalo (≈ 150 BPM). Serial: `[PULSO] Total: N | BPM: ~150` e `[ALERTA-LOCAL] ATIVO: BPM elevado | febre` (se a febre ainda estiver ativa). Dashboard: pontos no gráfico e `ALERTA: BPM simulado elevado` no status. **Capturas 15 e 18.** Um clique isolado, ou um intervalo acima de 2 s, não gera BPM válido; sem cliques por 4 s, volta a `indisponivel`.
2. **Faixas do gauge corporal:** 34 °C azul, 36,5 verde, 37,8 amarelo (sem alerta), 39 vermelho. **O DHT22 não é febre:** a 39 °C o gauge ambiental fica vermelho e o status mostra `Temperatura ambiental elevada`, sem `Febre` e sem LED aceso.
3. **Sem movimento:** no MPU6050, leve a rotação X a 100 °/s (`Movimento: ativo`, dashboard `Em movimento`), volte a 0 e espere 15 s sem mexer em nada. Esperado: `[ALERTA-LOCAL] ATIVO: ... sem movimento`, `Movimento: parado`, LED aceso e, no dashboard, `SEM MOVIMENTO (parado além do tempo limite)`. **Capturas 16 e 19.** Mexer de novo normaliza e reinicia a contagem.
4. **Alertas combinados:** febre, "parado" e cliques rápidos ao mesmo tempo mostram os três alertas no status, na ordem acima.
5. **Editor do Node-RED:** aba "CardioIA Fase 3" com o nó `mqtt in` conectado. A captura `20` já existe (feita sem o Wokwi em execução); refaça-a com o Wokwi rodando se quiser a barra de debug com mensagens recebidas. A captura dos alertas combinados ainda falta.
6. Na barra de debug, expanda uma mensagem e confira os 12 campos; sem cliques recentes, `bpm_valido` é `false`.

### 6. Verificação independente do broker (opcional)

Para separar "o ESP32 publicou" de "o Node-RED recebeu", abra https://www.hivemq.com/demos/websocket-client/ numa aba nova, conecte com os padrões do site e assine **somente** o tópico exato do contrato, sem curingas. Com o envio habilitado, as mensagens devem chegar a cada cerca de 2 s e bater com os ids do Serial. Depois desconecte e feche a aba.

### 7. Fora do alcance

Descarte por fila cheia (cerca de 1 h de coleta), persistência após reiniciar o ESP32 (a fila é RAM e se perde) e o som do buzzer (só o indicador visual do simulador).

## Capturas

Ficam em `evidencias/validacao-2026-11-04/`: `12` boot e coleta offline, `13` alerta de febre offline, `14` sincronização, `15` BPM por cliques, `16` sem movimento, `17` dashboard com febre, `18` dashboard com BPM e `19` dashboard com sem movimento, `20` editor do Node-RED, `21` dashboard com `SEM DADOS` (watchdog, depois do `f`) e `22` Wokwi offline depois do `f`. Falta a captura com os três alertas locais ao mesmo tempo. Todas as capturas de `12` a `22` (exceto a `20`, do editor) vêm da execução final com o firmware e o dashboard atuais. Os arquivos `01` a `09` vêm de execuções anteriores e de verificações auxiliares (veja "Execução registrada").

## Se algo falhar

- **Erro de compilação:** copie a mensagem inteira e confira `libraries.txt` (DHT sensor library for ESPx, PubSubClient, OneWire e DallasTemperature).
- **`DS18B20 ... NAO encontrado`:** confira o fio DQ no GPIO 4 e o resistor de 4,7 kΩ entre DQ e 3V3. **`MPU6050 ... NAO encontrado`:** confira SDA no GPIO 21, SCL no GPIO 22 e a alimentação.
- **`o` não conecta:** o Wi-Fi do simulador passa por um gateway do Wokwi que às vezes fica fora do ar por alguns minutos (erros 502 ou 503): o Serial fica em `[WIFI] Tentando conectar...`. Aguarde e repita `f` e `o`. `[MQTT] Falha, codigo: -2` indica rede ou broker inacessível.
- **Dashboard não atualiza, mas o Serial mostra "Publicacao aceita":** confira se o nó MQTT está "connected" e use o passo 6.
- **Simulação lenta (poucos por cento da velocidade):** feche outros programas pesados. O firmware só aceita um clique se ele durar mais de 40 ms **de tempo simulado**.
- **Gauge ambiental vermelho em 24 °C ou card "Group 1":** é o fluxo antigo no Node-RED; reimporte o JSON.
- **`SEM DADOS` aparece com o Wokwi rodando:** o watchdog usa 30 s reais e a simulação pode estar muito lenta (2 s simulados levando mais de 30 s reais). Feche programas pesados ou aguarde; se a simulação ficar nesse ritmo, o aviso não indica falha do firmware.

## Dicas para automatizar (opcional)

- Leia o Serial pelo console da página: cada linha chega como mensagem `[Serial] ...`. O monitor do Wokwi só guarda as últimas linhas na tela.
- Cadencie os cliques do botão pelo relógio da simulação, não pelo relógio real: a velocidade oscila entre 18 % e 80 %.
- Deixe a aba do Wokwi em primeiro plano (em segundo plano o navegador pausa a simulação) e abra o dashboard em outro navegador.
- O dashboard guarda o estado de mensagens antigas: os critérios do teste devem ser algo que só o Wokwi publica agora.

## Depois do teste

1. Salve as capturas em `evidencias/` e atualize as referências em [`README.md`](../README.md) e [`relatorio_mqtt.md`](relatorio_mqtt.md).
2. Se algo divergir do esperado, corrija o firmware ou a documentação; se mudar limiares, siga o [contrato MQTT](contrato_mqtt.md).
3. Regenere os PDFs dos relatórios com `python fase3/docs/gerar_pdfs.py` (pandoc e Edge ou Chrome instalados).

## Execução registrada em 2026-11-04

- **Wokwi, execução final (38 de 38):** o `sketch.ino` do repositório (844 linhas, com o bloco opcional de Wi-Fi) foi colado no editor da página do projeto do link (ID 479773169716093953), em sessão anônima de navegador automatizado (Playwright com Edge), a 18 % a 43 % da velocidade real, com o dashboard do Node-RED local (fluxo do repositório) lendo o broker público. Compilou no Wokwi sem erro e o Serial foi lido pelo console da página. Verificados: boot do firmware (DS18B20 e MPU6050 encontrados, modo OFFLINE, sem linhas `[WIFI]` ou `[MQTT]`); coleta offline com ids 1 a 6 sem pulos; alerta local de febre com o DS18B20 em 39 °C (LED aceso, indicador de som no buzzer) sem nada chegar ao dashboard; após `o`, Wi-Fi e broker conectados, leituras #1 a #9 publicadas em ordem, cada uma com o resumo do dado, e `[SYNC] Fila de publicacoes pendentes esvaziada.`; dashboard com banner `ALERTA` e `ALERTA: Febre (temperatura corporal elevada)`; 14 cliques a cerca de 150 BPM (`[PULSO] Total: 14 | BPM: 150.4`), com alerta local de BPM elevado e o alerta de BPM no dashboard; MPU6050 girado e devolvido ao repouso, com `sem movimento` após 15,0 s simulados no Serial e no dashboard; `f`, com a coleta e os alertas locais continuando e, 27 s depois da última leitura, `SEM DADOS` no dashboard; `o` de novo, com as leituras #26 a #31 em ordem e o banner saindo de `SEM DADOS`. Capturas `12` a `19`, `21` e `22`. **Não verificado:** o som do buzzer (só o indicador visual do simulador). A sessão era anônima (aba `sketch.ino ●` nas capturas); o dono da conta salvou depois o mesmo arquivo no projeto, e `sketch.ino` e `diagram.json` do projeto foram conferidos por diff como idênticos aos do repositório. A leitura vem sempre do ESP32 simulado; não há hardware físico.
- **Histórico:** no início do dia o projeto do link não tinha `sketch.ino` (o código estava na aba `README.md`) e a compilação falhava com `setup()` e `loop()` indefinidos (captura `06`); o arquivo foi adicionado em 2026-11-04 e uma primeira execução completa (32 verificações, com o firmware ainda sem o resumo do dado no Serial e o dashboard sem watchdog) foi substituída pela execução final acima. Uma execução anterior no projeto `cardioiaiot` (ID 479766849694291969), com a mesma versão do firmware daquela primeira execução, está nas capturas `01` e `05`.
- **Node-RED + MQTT:** Node-RED 5.0.9 e Dashboard 2.0 1.33.0 foram iniciados em ambiente isolado na porta 1881. O nó MQTT conectou ao broker público. Publiquei somente uma mensagem de teste sintética no tópico do projeto (ID 99004, BPM 130, temperaturas 39 °C, movimento `parado`, máscara 7); o dashboard atualizou os gauges, movimento, alertas locais e status Fog esperados. Isso valida o consumidor MQTT/dashboard, mas não substitui a publicação do ESP32 simulado no Wokwi (a execução acima).
- **Capturas** em `evidencias/validacao-2026-11-04/`: `12` a `19`, `21` e `22` (execução final no Wokwi e dashboard), `01` e `05` (execução anterior), `06` (falha de build anterior), `07` e `08` (dashboard com mensagem sintética, que não vem do Wokwi), `09` (saída real do `npm test`, 95 testes aprovados) e `20` (editor do Node-RED, sem o Wokwi em execução).
- **Verificações posteriores (2026-11-04, tarde):** (a) o firmware compila no PlatformIO (espressif32 8.0.0, Arduino-ESP32 3.3.12, o mesmo core do Wokwi) com RAM 32,5 % e flash 77,9 %, antes e depois das mudanças do dia; (b) o watchdog, o banner e o aviso clínico foram exercitados num Node-RED 5.0.9 real, com Dashboard 2.0 1.33.0 e um broker MQTT **local**, lendo o DOM do dashboard: 13 de 13 conferências (dado sintético gerado pelo teste, não do Wokwi; o script não está no repositório); (c) a captura 20 foi feita numa instância isolada do Node-RED com o fluxo do repositório, conectada ao broker público (só assinando o tópico). O firmware atual também foi executado no Wokwi (primeiro item desta seção), numa sessão anônima e sem salvar.
