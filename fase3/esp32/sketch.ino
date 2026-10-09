#include <Arduino.h>
#include <DHTesp.h>
#include <WiFi.h>
#include <PubSubClient.h>

// =====================================================
// CardioIA - Fase 3
// Monitoramento IoT com resiliencia offline e MQTT
//
// Sensores:
// - DHT22: temperatura e umidade
// - Botao: pulsos cardiacos simulados
//
// Edge Computing:
// - Coleta local
// - Armazenamento em fila circular
// - Sincronizacao apos reconexao
// =====================================================

// ---------------- CONFIGURACOES ----------------

const int PINO_DHT = 15;
const int PINO_BOTAO = 18;

const unsigned long INTERVALO_COLETA = 2000;
const unsigned long DEBOUNCE_MS = 40;
const unsigned long TIMEOUT_PULSO = 4000;

// 1800 leituras x 2 segundos = aproximadamente 1 hora
const int CAPACIDADE_FILA = 1800;

// ---------------- SENSORES ----------------

DHTesp sensorDHT;

unsigned long ultimaColeta = 0;
unsigned long ultimoPulso = 0;
unsigned long ultimaMudancaBotao = 0;

int estadoAnteriorBotao = HIGH;
int estadoEstavelBotao = HIGH;

float bpm = 0;
unsigned int totalPulsos = 0;

// ---------------- CONECTIVIDADE ----------------

// false: desconectado
// true: conectado
// Inicialmente offline para demonstrar a resiliencia.
// f/o alternam a transmissao de forma controlada para testes.
// Em modo offline a coleta local continua funcionando.
bool envioHabilitado = false;

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_SENHA = "";
const char* BROKER_MQTT = "broker.hivemq.com";
const uint16_t PORTA_MQTT = 1883;
const char* TOPICO_MQTT = "cardioia/fiap/fase3/enzf-477362937220720641/sinais";
const char* ID_CLIENTE = "cardioia-esp32-enzf-477362937220720641";

WiFiClient clienteRede;
PubSubClient mqtt(clienteRede);
unsigned long ultimaTentativaWiFi = 0;
unsigned long ultimaTentativaMQTT = 0;
const unsigned long INTERVALO_RECONEXAO = 5000;

bool conexaoPronta() {
  return envioHabilitado && WiFi.status() == WL_CONNECTED && mqtt.connected();
}

// As tentativas sao espacadas, sem bloquear a leitura dos sensores.
void manterConexao() {
  if (!envioHabilitado) return;

  unsigned long agora = millis();
  if (WiFi.status() != WL_CONNECTED) {
    if (ultimaTentativaWiFi == 0 || agora - ultimaTentativaWiFi >= INTERVALO_RECONEXAO) {
      ultimaTentativaWiFi = agora;
      Serial.println("[WIFI] Tentando conectar...");
      WiFi.begin(WIFI_SSID, WIFI_SENHA, 6);
    }
    return;
  }

  if (!mqtt.connected()) {
    if (ultimaTentativaMQTT == 0 || agora - ultimaTentativaMQTT >= INTERVALO_RECONEXAO) {
      ultimaTentativaMQTT = agora;
      Serial.println("[MQTT] Tentando conectar ao broker...");
      if (mqtt.connect(ID_CLIENTE)) {
        Serial.println("[MQTT] Conectado ao broker!");
      } else {
        Serial.print("[MQTT] Falha, codigo: ");
        Serial.println(mqtt.state());
      }
    }
    return;
  }

  mqtt.loop();
}

// ---------------- ARMAZENAMENTO LOCAL ----------------

// Estrutura que representa uma leitura completa.
struct Leitura {
  unsigned long id;
  unsigned long timestamp;
  float temperatura;
  float umidade;
  float bpm;
  bool bpmValido;
};

// Declarações antecipadas das funções
void armazenarLeitura(Leitura novaLeitura);
bool transmitirLeitura(const Leitura &leitura);

// Fila circular com capacidade fixa.
Leitura fila[CAPACIDADE_FILA];

// Indice da leitura mais antiga.
int inicioFila = 0;

// Numero de leituras armazenadas.
int quantidadeFila = 0;

// Identificador sequencial das leituras.
unsigned long proximoId = 1;

// Conta quantas leituras foram perdidas por falta de espaco.
unsigned long leiturasDescartadas = 0;


// =====================================================
// ARMAZENAMENTO: adicionar leitura
// =====================================================

void armazenarLeitura(Leitura novaLeitura) {

  // Quando a fila esta cheia, a leitura mais antiga
  // e descartada para abrir espaco.
  if (quantidadeFila == CAPACIDADE_FILA) {
    inicioFila = (inicioFila + 1) % CAPACIDADE_FILA;
    quantidadeFila--;
    leiturasDescartadas++;

    Serial.println("[AVISO] Fila cheia: leitura antiga descartada.");
  }

  // Calcula a proxima posicao livre da fila circular.
  int posicao = (inicioFila + quantidadeFila) % CAPACIDADE_FILA;

  fila[posicao] = novaLeitura;
  quantidadeFila++;

  Serial.print("[EDGE] Leitura #");
  Serial.print(novaLeitura.id);
  Serial.print(" armazenada. Pendentes: ");
  Serial.println(quantidadeFila);
}


// =====================================================
// TRANSMISSAO MQTT (QoS 0)
// =====================================================

bool transmitirLeitura(const Leitura &leitura) {
  if (!conexaoPronta()) return false;

  char payload[320];
  int tamanho = snprintf(
    payload, sizeof(payload),
    "{\"dispositivo\":\"cardioia-esp32-01\",\"id\":%lu,"
    "\"timestamp_ms\":%lu,\"temperatura\":%.1f,\"umidade\":%.1f,"
    "\"bpm\":%.1f,\"bpm_valido\":%s}",
    leitura.id, leitura.timestamp, leitura.temperatura, leitura.umidade,
    leitura.bpm, leitura.bpmValido ? "true" : "false"
  );

  if (tamanho < 0 || tamanho >= (int)sizeof(payload)) {
    Serial.println("[MQTT] Erro: payload muito grande.");
    return false;
  }

  // publish() confirma aceite pelo cliente local, NAO entrega garantida.
  if (!mqtt.publish(TOPICO_MQTT, payload)) {
    Serial.println("[MQTT] Falha ao publicar; leitura mantida na fila.");
    return false;
  }

  Serial.print("[MQTT] Publicacao aceita: #");
  Serial.println(leitura.id);
  return true;
}


// =====================================================
// SINCRONIZACAO DA FILA
// =====================================================

void sincronizarLeituras() {

  if (!conexaoPronta() || quantidadeFila == 0) {
    return;
  }

  // Limita o envio a 10 leituras por passagem do loop,
  // evitando monopolizar o processamento por muito tempo.
  int enviadasNestaRodada = 0;

  while (conexaoPronta() &&
         quantidadeFila > 0 &&
         enviadasNestaRodada < 10) {

    Leitura &leitura = fila[inicioFila];

    if (!transmitirLeitura(leitura)) {
      break;
    }

    // Remove apos aceite local da publicacao MQTT (QoS 0).
    inicioFila = (inicioFila + 1) % CAPACIDADE_FILA;
    quantidadeFila--;
    enviadasNestaRodada++;
  }

  if (quantidadeFila == 0 && enviadasNestaRodada > 0) {
    Serial.println("[SYNC] Fila de publicacoes pendentes esvaziada.");
  }
}


// =====================================================
// COMANDOS DE CONECTIVIDADE
// =====================================================

// No Monitor Serial:
// F = simular queda da conexao
// O = restaurar conexao
// S = consultar status

void verificarComandos() {

  while (Serial.available() > 0) {

    char comando = Serial.read();

    if (comando == 'F' || comando == 'f') {
      envioHabilitado = false;
      mqtt.disconnect();
      Serial.println("[OFFLINE] Transmissao MQTT desabilitada; coleta continua.");
    }

    else if (comando == 'O' || comando == 'o') {
      envioHabilitado = true;
      ultimaTentativaWiFi = 0;
      ultimaTentativaMQTT = 0;
      Serial.println("[ONLINE] Transmissao MQTT habilitada.");
      Serial.println("[SYNC] Iniciando envio dos dados pendentes...");
    }

    else if (comando == 'S' || comando == 's') {
      Serial.println("------- STATUS CARDIOIA -------");

      Serial.print("Conectividade: ");
      Serial.println(conexaoPronta() ? "ONLINE (MQTT)" : "OFFLINE (envio indisponivel)");

      Serial.print("Leituras pendentes: ");
      Serial.println(quantidadeFila);

      Serial.print("Leituras descartadas: ");
      Serial.println(leiturasDescartadas);

      Serial.println("-------------------------------");
    }
  }
}


// =====================================================
// LEITURA DOS BATIMENTOS SIMULADOS
// =====================================================

void verificarBatimentos(unsigned long agora) {

  int leituraBotao = digitalRead(PINO_BOTAO);

  if (leituraBotao != estadoAnteriorBotao) {
    ultimaMudancaBotao = agora;
  }

  if (agora - ultimaMudancaBotao >= DEBOUNCE_MS) {

    if (leituraBotao != estadoEstavelBotao) {
      estadoEstavelBotao = leituraBotao;

      if (estadoEstavelBotao == LOW) {
        totalPulsos++;

        if (ultimoPulso != 0) {

          unsigned long intervalo = agora - ultimoPulso;

          if (intervalo >= 300 && intervalo <= 2000) {
            bpm = 60000.0 / intervalo;
          } else {
            bpm = 0;
          }
        }

        ultimoPulso = agora;

        Serial.print("[PULSO] Total: ");
        Serial.print(totalPulsos);
        Serial.print(" | BPM: ");
        Serial.println(bpm, 1);
      }
    }
  }

  estadoAnteriorBotao = leituraBotao;

  if (ultimoPulso != 0 &&
      agora - ultimoPulso >= TIMEOUT_PULSO) {

    bpm = 0;
    ultimoPulso = 0;
  }
}


// =====================================================
// COLETA DOS SINAIS VITAIS
// =====================================================

void coletarSinais(unsigned long agora) {

  if (agora - ultimaColeta < INTERVALO_COLETA) {
    return;
  }

  ultimaColeta = agora;

  TempAndHumidity dados = sensorDHT.getTempAndHumidity();

  if (isnan(dados.temperature) || isnan(dados.humidity)) {
    Serial.println("[ERRO] Falha na leitura do DHT22.");
    return;
  }

  // Cria um registro completo da leitura.
  Leitura novaLeitura;

  novaLeitura.id = proximoId++;
  novaLeitura.timestamp = agora;
  novaLeitura.temperatura = dados.temperature;
  novaLeitura.umidade = dados.humidity;
  novaLeitura.bpm = bpm;

  // Sem dois pulsos recentes, nao existe estimativa valida.
  novaLeitura.bpmValido = (ultimoPulso != 0 && bpm > 0);

  Serial.println("------ NOVA LEITURA ------");

  Serial.print("Temperatura: ");
  Serial.print(novaLeitura.temperatura, 1);
  Serial.println(" C");

  Serial.print("Umidade: ");
  Serial.print(novaLeitura.umidade, 1);
  Serial.println(" %");

  Serial.print("BPM simulado: ");
  if (novaLeitura.bpmValido) {
    Serial.println(novaLeitura.bpm, 1);
  } else {
    Serial.println("indisponivel");
  }

  Serial.print("Conexao: ");
  Serial.println(conexaoPronta() ? "ONLINE (MQTT)" : "OFFLINE (envio indisponivel)");

  // Toda leitura entra primeiro na fila.
  // Se estiver online, sera sincronizada em seguida.
  armazenarLeitura(novaLeitura);
}


// =====================================================
// INICIALIZACAO
// =====================================================

void setup() {

  Serial.begin(115200);

  sensorDHT.setup(PINO_DHT, DHTesp::DHT22);
  pinMode(PINO_BOTAO, INPUT_PULLUP);
  mqtt.setServer(BROKER_MQTT, PORTA_MQTT);
  mqtt.setBufferSize(512);

  Serial.println("=================================");
  Serial.println("CardioIA - Fase 3: Edge + MQTT");
  Serial.println("=================================");
  Serial.println("DHT22 e simulador BPM iniciados.");
  Serial.println("Modo inicial: OFFLINE");
  Serial.println("Comandos: F=offline | O=online | S=status");
  Serial.println("=================================");
}


// =====================================================
// LOOP PRINCIPAL
// =====================================================

void loop() {

  unsigned long agora = millis();

  // Recebe comandos digitados no Monitor Serial.
  verificarComandos();

  // Detecta os cliques no botao continuamente.
  verificarBatimentos(agora);

  // Coleta temperatura, umidade e BPM.
  coletarSinais(agora);

  // Gerencia Wi-Fi/MQTT sem bloquear o fluxo de coleta.
  manterConexao();

  // Se houver conexao, envia as leituras pendentes.
  sincronizarLeituras();
}