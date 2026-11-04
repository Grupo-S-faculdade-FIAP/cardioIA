#include <Arduino.h>
#include <DHTesp.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>

#if __has_include("wifi_config.h")
#include "wifi_config.h"
#endif

#ifndef CARDIOIA_WIFI_SSID
#define CARDIOIA_WIFI_SSID "Wokwi-GUEST"
#endif

#ifndef CARDIOIA_WIFI_PASSWORD
#define CARDIOIA_WIFI_PASSWORD ""
#endif

#ifndef CARDIOIA_WIFI_CHANNEL
#define CARDIOIA_WIFI_CHANNEL 6
#endif

// =====================================================
// CardioIA - Fase 3
// Monitoramento IoT com resiliencia offline, MQTT e
// alerta local (Edge)
//
// Sensores:
// - DHT22: temperatura e umidade do AMBIENTE
// - DS18B20: temperatura CORPORAL (pele) simulada
// - MPU6050: movimento (acelerometro + giroscopio)
// - Botao: pulsos cardiacos simulados (BPM)
//
// Atuadores (alerta local, funciona mesmo offline):
// - LED: aceso quando existe qualquer alerta
// - Buzzer: bipes quando ha alerta critico (BPM ou febre)
//
// Edge Computing:
// - Coleta local
// - Armazenamento em fila circular
// - Sincronizacao apos reconexao
// - Avaliacao de alertas no proprio dispositivo
// =====================================================

// ---------------- CONFIGURACOES ----------------

const int PINO_DHT = 15;
const int PINO_BOTAO = 18;
const int PINO_DS18B20 = 4;
const int PINO_SDA = 21;
const int PINO_SCL = 22;
const int PINO_LED = 26;
const int PINO_BUZZER = 27;

const unsigned long INTERVALO_COLETA = 2000;
const unsigned long DEBOUNCE_MS = 40;
const unsigned long TIMEOUT_PULSO = 4000;

// 1800 leituras x 2 segundos = aproximadamente 1 hora
const int CAPACIDADE_FILA = 1800;

// Limiares de alerta. Sao os mesmos do dashboard Node-RED
// (regras demonstrativas, nao criterios de diagnostico).
const float LIMITE_BPM = 120.0;
const float LIMITE_FEBRE = 38.0;

// Tempo parado para alertar. 15 s facilita a demonstracao;
// em uso real seriam minutos.
const unsigned long TEMPO_SEM_MOVIMENTO_MS = 15000;

// Variacao de aceleracao (g) entre amostras e giro (graus/s)
// a partir dos quais o corpo e considerado em movimento.
const float LIMIAR_VARIACAO_ACEL_G = 0.05;
const float LIMIAR_GIRO_DPS = 10.0;

// ---------------- SENSORES ----------------

DHTesp sensorDHT;

unsigned long ultimaColeta = 0;
unsigned long ultimoPulso = 0;
unsigned long ultimaMudancaBotao = 0;

int estadoAnteriorBotao = HIGH;
int estadoEstavelBotao = HIGH;

float bpm = 0;
unsigned int totalPulsos = 0;

// Sem dois pulsos recentes, nao existe estimativa valida.
bool bpmValidoAgora() {
  return ultimoPulso != 0 && bpm > 0;
}

// ---------------- TEMPERATURA CORPORAL (DS18B20) ----------------

OneWire barramentoCorpo(PINO_DS18B20);
DallasTemperature sensorCorpo(&barramentoCorpo);

// A conversao do DS18B20 leva ate 750 ms. Para nao bloquear a
// leitura do botao, pedimos a conversao e lemos o resultado depois.
const unsigned long TEMPO_CONVERSAO_CORPO_MS = 800;
unsigned long inicioConversaoCorpo = 0;
float tempCorporal = 0;
bool tempCorporalValida = false;

void iniciarSensorCorpo() {
  sensorCorpo.begin();
  sensorCorpo.setWaitForConversion(false);
  sensorCorpo.requestTemperatures();
  inicioConversaoCorpo = millis();
}

void atualizarTemperaturaCorporal(unsigned long agora) {
  if (agora - inicioConversaoCorpo < TEMPO_CONVERSAO_CORPO_MS) return;

  float leitura = sensorCorpo.getTempCByIndex(0);

  // -127 indica sensor desconectado.
  tempCorporalValida = (leitura > -55.0 && leitura < 125.0);
  if (tempCorporalValida) {
    tempCorporal = leitura;
  }

  sensorCorpo.requestTemperatures();
  inicioConversaoCorpo = agora;
}

// ---------------- MOVIMENTO (MPU6050) ----------------

const uint8_t MPU_ENDERECO = 0x68;
const unsigned long INTERVALO_MPU = 100;
const unsigned long INTERVALO_MPU_AUSENTE = 5000;

enum EstadoMovimento {
  MOV_INDISPONIVEL = 0,  // MPU6050 nao responde
  MOV_AGUARDANDO = 1,    // ainda nao houve movimento desde o boot
  MOV_ATIVO = 2,         // movimento nos ultimos TEMPO_SEM_MOVIMENTO_MS
  MOV_PARADO = 3         // parado ha TEMPO_SEM_MOVIMENTO_MS ou mais
};

bool mpuPresente = false;
uint8_t estadoMovimento = MOV_INDISPONIVEL;
float aceleracaoG = 0;
bool temAmostraAnterior = false;
float axAnterior = 0, ayAnterior = 0, azAnterior = 0;
unsigned long ultimaLeituraMPU = 0;
unsigned long ultimoMovimento = 0;

// O alerta de "sem movimento" so vale depois do primeiro movimento
// detectado: assim um dispositivo ainda guardado, em repouso, nao alerta.
bool movimentoArmado = false;

const char* nomeMovimento(uint8_t estado) {
  switch (estado) {
    case MOV_AGUARDANDO: return "aguardando";
    case MOV_ATIVO: return "ativo";
    case MOV_PARADO: return "parado";
    default: return "indisponivel";
  }
}

bool iniciarMPU() {
  Wire.begin(PINO_SDA, PINO_SCL);
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x6B);  // PWR_MGMT_1
  Wire.write(0);     // sai do modo sleep
  return Wire.endTransmission() == 0;
}

// Le aceleracao (g) e giro (graus/s) nas escalas padrao: +-2 g e +-250 graus/s.
bool lerMPU(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x3B);  // ACCEL_XOUT_H
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ENDERECO, (size_t)14, true) != 14) return false;

  int16_t bruto[7];
  for (int i = 0; i < 7; i++) {
    uint8_t alto = Wire.read();
    uint8_t baixo = Wire.read();
    bruto[i] = (int16_t)((alto << 8) | baixo);
  }

  ax = bruto[0] / 16384.0;
  ay = bruto[1] / 16384.0;
  az = bruto[2] / 16384.0;
  // bruto[3] e a temperatura interna do chip, nao usada.
  gx = bruto[4] / 131.0;
  gy = bruto[5] / 131.0;
  gz = bruto[6] / 131.0;
  return true;
}

void atualizarMovimento(unsigned long agora) {
  unsigned long intervalo = mpuPresente ? INTERVALO_MPU : INTERVALO_MPU_AUSENTE;
  if (agora - ultimaLeituraMPU < intervalo) return;
  ultimaLeituraMPU = agora;

  float ax, ay, az, gx, gy, gz;

  if (!mpuPresente) {
    // Sensor ausente: tenta religar de tempos em tempos.
    mpuPresente = iniciarMPU();
    if (!mpuPresente) {
      estadoMovimento = MOV_INDISPONIVEL;
      return;
    }
  }

  if (!lerMPU(ax, ay, az, gx, gy, gz)) {
    mpuPresente = false;
    estadoMovimento = MOV_INDISPONIVEL;
    return;
  }

  aceleracaoG = sqrtf(ax * ax + ay * ay + az * az);
  float giroDps = sqrtf(gx * gx + gy * gy + gz * gz);

  // Movimento = a aceleracao esta variando ou o corpo esta girando.
  // Um valor constante (parado, mesmo inclinado) nao conta.
  bool houveMovimento = giroDps > LIMIAR_GIRO_DPS;
  if (temAmostraAnterior) {
    float dx = ax - axAnterior;
    float dy = ay - ayAnterior;
    float dz = az - azAnterior;
    if (sqrtf(dx * dx + dy * dy + dz * dz) > LIMIAR_VARIACAO_ACEL_G) {
      houveMovimento = true;
    }
  }
  axAnterior = ax;
  ayAnterior = ay;
  azAnterior = az;
  temAmostraAnterior = true;

  if (houveMovimento) {
    ultimoMovimento = agora;
    movimentoArmado = true;
  }

  if (!movimentoArmado) {
    estadoMovimento = MOV_AGUARDANDO;
  } else if (agora - ultimoMovimento >= TEMPO_SEM_MOVIMENTO_MS) {
    estadoMovimento = MOV_PARADO;
  } else {
    estadoMovimento = MOV_ATIVO;
  }
}

// ---------------- ALERTA LOCAL (EDGE) ----------------

// Cada alerta e um bit; o conjunto viaja na mensagem MQTT.
const uint8_t ALERTA_BPM = 1;
const uint8_t ALERTA_FEBRE = 2;
const uint8_t ALERTA_SEM_MOVIMENTO = 4;

const unsigned int FREQUENCIA_BUZZER = 2000;
const unsigned long BIPE_PERIODO_MS = 1000;
const unsigned long BIPE_DURACAO_MS = 150;

uint8_t alertasAtuais = 0;
bool buzzerLigado = false;

void iniciarBuzzer() {
  pinMode(PINO_BUZZER, OUTPUT);
#if !(defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3)
  // Core 2.x do Arduino-ESP32 nao tem tone(): usa o LEDC.
  ledcSetup(0, FREQUENCIA_BUZZER, 8);
  ledcAttachPin(PINO_BUZZER, 0);
#endif
}

void ligarBuzzer(bool ligado) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  if (ligado) {
    tone(PINO_BUZZER, FREQUENCIA_BUZZER);
  } else {
    noTone(PINO_BUZZER);
  }
#else
  ledcWriteTone(0, ligado ? FREQUENCIA_BUZZER : 0);
#endif
  buzzerLigado = ligado;
}

uint8_t calcularAlertas() {
  uint8_t alertas = 0;

  if (bpmValidoAgora() && bpm > LIMITE_BPM) {
    alertas |= ALERTA_BPM;
  }
  if (tempCorporalValida && tempCorporal > LIMITE_FEBRE) {
    alertas |= ALERTA_FEBRE;
  }
  if (estadoMovimento == MOV_PARADO) {
    alertas |= ALERTA_SEM_MOVIMENTO;
  }
  return alertas;
}

void descreverAlertas(uint8_t alertas, char *saida, size_t tamanho) {
  saida[0] = '\0';

  if (alertas == 0) {
    strlcat(saida, "nenhum", tamanho);
    return;
  }

  const char *separador = "";
  if (alertas & ALERTA_BPM) {
    strlcat(saida, "BPM elevado", tamanho);
    separador = " | ";
  }
  if (alertas & ALERTA_FEBRE) {
    strlcat(saida, separador, tamanho);
    strlcat(saida, "febre", tamanho);
    separador = " | ";
  }
  if (alertas & ALERTA_SEM_MOVIMENTO) {
    strlcat(saida, separador, tamanho);
    strlcat(saida, "sem movimento", tamanho);
  }
}

// Avalia os alertas e aciona LED e buzzer. Roda a cada passagem do
// loop, sem depender de Wi-Fi, MQTT ou do dashboard.
void atualizarAlertasLocais(unsigned long agora) {
  uint8_t novos = calcularAlertas();

  if (novos != alertasAtuais) {
    alertasAtuais = novos;

    char texto[64];
    descreverAlertas(alertasAtuais, texto, sizeof(texto));
    if (alertasAtuais == 0) {
      Serial.println("[ALERTA-LOCAL] Normalizado.");
    } else {
      Serial.print("[ALERTA-LOCAL] ATIVO: ");
      Serial.println(texto);
    }
  }

  digitalWrite(PINO_LED, alertasAtuais != 0 ? HIGH : LOW);

  // Buzzer: bipe curto a cada segundo, so para alertas criticos.
  bool critico = (alertasAtuais & (ALERTA_BPM | ALERTA_FEBRE)) != 0;
  bool bipe = critico && (agora % BIPE_PERIODO_MS) < BIPE_DURACAO_MS;
  if (bipe != buzzerLigado) {
    ligarBuzzer(bipe);
  }
}

// ---------------- CONECTIVIDADE ----------------

// false: desconectado
// true: conectado
// Inicialmente offline para demonstrar a resiliencia.
// f/o alternam a transmissao de forma controlada para testes.
// Em modo offline a coleta local continua funcionando.
bool envioHabilitado = false;

const char* WIFI_SSID = CARDIOIA_WIFI_SSID;
const char* WIFI_SENHA = CARDIOIA_WIFI_PASSWORD;
const uint8_t CANAL_WIFI = CARDIOIA_WIFI_CHANNEL;
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
      WiFi.begin(WIFI_SSID, WIFI_SENHA, CANAL_WIFI);
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

// Estrutura que representa uma leitura completa (32 bytes).
struct Leitura {
  unsigned long id;
  unsigned long timestamp;
  float temperatura;
  float umidade;
  float bpm;
  float tempCorporal;
  float aceleracao;
  bool bpmValido;
  bool tempCorporalValida;
  uint8_t estadoMovimento;
  uint8_t alertas;
};

// Declaracoes antecipadas das funcoes
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

  char payload[384];
  int tamanho = snprintf(
    payload, sizeof(payload),
    "{\"dispositivo\":\"cardioia-esp32-01\",\"id\":%lu,"
    "\"timestamp_ms\":%lu,\"temperatura\":%.1f,\"umidade\":%.1f,"
    "\"temp_corporal\":%.1f,\"temp_corporal_valida\":%s,"
    "\"bpm\":%.1f,\"bpm_valido\":%s,"
    "\"movimento\":\"%s\",\"aceleracao_g\":%.2f,\"alertas_locais\":%u}",
    leitura.id, leitura.timestamp, leitura.temperatura, leitura.umidade,
    leitura.tempCorporal, leitura.tempCorporalValida ? "true" : "false",
    leitura.bpm, leitura.bpmValido ? "true" : "false",
    nomeMovimento(leitura.estadoMovimento), leitura.aceleracao,
    (unsigned int)leitura.alertas
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

      Serial.print("Temp. corporal: ");
      if (tempCorporalValida) {
        Serial.print(tempCorporal, 1);
        Serial.println(" C");
      } else {
        Serial.println("indisponivel");
      }

      Serial.print("Movimento: ");
      Serial.println(nomeMovimento(estadoMovimento));

      char texto[64];
      descreverAlertas(alertasAtuais, texto, sizeof(texto));
      Serial.print("Alertas locais: ");
      Serial.println(texto);

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
  novaLeitura.bpmValido = bpmValidoAgora();
  novaLeitura.tempCorporal = tempCorporalValida ? tempCorporal : 0;
  novaLeitura.tempCorporalValida = tempCorporalValida;
  novaLeitura.aceleracao = mpuPresente ? aceleracaoG : 0;
  novaLeitura.estadoMovimento = estadoMovimento;
  novaLeitura.alertas = alertasAtuais;

  Serial.println("------ NOVA LEITURA ------");

  Serial.print("Temperatura: ");
  Serial.print(novaLeitura.temperatura, 1);
  Serial.println(" C");

  Serial.print("Umidade: ");
  Serial.print(novaLeitura.umidade, 1);
  Serial.println(" %");

  Serial.print("Temp. corporal: ");
  if (novaLeitura.tempCorporalValida) {
    Serial.print(novaLeitura.tempCorporal, 1);
    Serial.println(" C");
  } else {
    Serial.println("indisponivel");
  }

  Serial.print("BPM simulado: ");
  if (novaLeitura.bpmValido) {
    Serial.println(novaLeitura.bpm, 1);
  } else {
    Serial.println("indisponivel");
  }

  Serial.print("Movimento: ");
  Serial.print(nomeMovimento(novaLeitura.estadoMovimento));
  if (mpuPresente) {
    Serial.print(" (|a|=");
    Serial.print(novaLeitura.aceleracao, 2);
    Serial.println(" g)");
  } else {
    Serial.println();
  }

  char texto[64];
  descreverAlertas(novaLeitura.alertas, texto, sizeof(texto));
  Serial.print("Alertas locais: ");
  Serial.println(texto);

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
  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, LOW);
  iniciarBuzzer();
  iniciarSensorCorpo();
  mpuPresente = iniciarMPU();
  mqtt.setServer(BROKER_MQTT, PORTA_MQTT);
  mqtt.setBufferSize(512);

  Serial.println("=================================");
  Serial.println("CardioIA - Fase 3: Edge + MQTT");
  Serial.println("=================================");
  Serial.println("DHT22 e simulador BPM iniciados.");
  Serial.print("DS18B20 (temp. corporal): ");
  Serial.println(sensorCorpo.getDeviceCount() > 0 ? "encontrado" : "NAO encontrado");
  Serial.print("MPU6050 (movimento): ");
  Serial.println(mpuPresente ? "encontrado" : "NAO encontrado");
  Serial.println("Modo inicial: OFFLINE");
  Serial.println("Comandos: F=offline | O=online | S=status");
  Serial.println("=================================");

  // Autoteste do alerta local: LED e buzzer por 200 ms.
  digitalWrite(PINO_LED, HIGH);
  ligarBuzzer(true);
  delay(200);
  ligarBuzzer(false);
  digitalWrite(PINO_LED, LOW);
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

  // Atualiza temperatura corporal e movimento.
  atualizarTemperaturaCorporal(agora);
  atualizarMovimento(agora);

  // Avalia alertas e aciona LED/buzzer, mesmo offline.
  atualizarAlertasLocais(agora);

  // Coleta temperatura, umidade, BPM e demais sinais.
  coletarSinais(agora);

  // Gerencia Wi-Fi/MQTT sem bloquear o fluxo de coleta.
  manterConexao();

  // Se houver conexao, envia as leituras pendentes.
  sincronizarLeituras();
}
