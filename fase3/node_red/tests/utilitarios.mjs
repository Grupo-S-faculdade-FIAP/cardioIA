// Utilitários dos testes da camada Fog (Node-RED) da Fase 3.
// Sem dependências: só módulos nativos do Node.js (>= 20).
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));

const RAIZ_FASE3 = path.resolve(AQUI, '..', '..');

export const CAMINHOS = {
  fluxo: path.join(RAIZ_FASE3, 'node_red', 'cardioia-fase3-flow.json'),
  firmware: path.join(RAIZ_FASE3, 'esp32', 'sketch.ino'),
  contrato: path.join(RAIZ_FASE3, 'docs', 'contrato_mqtt.md'),
  readmeRaiz: path.join(RAIZ_FASE3, '..', 'README.md'),
  readmeFase3: path.join(RAIZ_FASE3, 'README.md'),
  readmeNodeRed: path.join(RAIZ_FASE3, 'node_red', 'README.md'),
  roteiro: path.join(RAIZ_FASE3, 'docs', 'roteiro_teste_wokwi.md'),
  relatorioEdge: path.join(RAIZ_FASE3, 'docs', 'relatorio_edge.md'),
  relatorioMqtt: path.join(RAIZ_FASE3, 'docs', 'relatorio_mqtt.md'),
};

// Lê um arquivo de texto normalizando BOM e quebras de linha: o repositório pode estar
// com CRLF (Windows) ou LF (Linux/CI), e os testes não podem depender disso.
export function lerTexto(caminho) {
  return fs.readFileSync(caminho, 'utf8').replace(/^﻿/, '').replace(/\r\n/g, '\n');
}

// ---------------------------------------------------------------- fluxo Node-RED

export function carregarFluxo() {
  return JSON.parse(lerTexto(CAMINHOS.fluxo));
}

export function noPorNome(fluxo, nome) {
  const nos = fluxo.filter((n) => n.name === nome);
  if (nos.length !== 1) {
    throw new Error(`esperava exatamente 1 nó chamado "${nome}" no fluxo, achei ${nos.length}`);
  }
  return nos[0];
}

export function nosFuncao(fluxo) {
  return fluxo.filter((n) => n.type === 'function');
}

// Executa o código de um nó "function" como o Node-RED faz: o código vira o corpo de uma
// função assíncrona de `msg`, rodando num contexto isolado. Devolve a mensagem ou null
// (null = o nó descartou a mensagem, nada chega ao widget).
// Atenção: o resultado vem de outro "realm" do V8; compare campos (payload, topic) e não o
// objeto inteiro com deepStrictEqual.
export async function executarFuncao(fluxo, nome, payload) {
  const no = noPorNome(fluxo, nome);
  if (no.type !== 'function') throw new Error(`"${nome}" não é um nó function`);

  const memoria = () => ({ get: () => undefined, set: () => {}, keys: () => [] });
  const contexto = vm.createContext({
    node: { warn() {}, error() {}, log() {}, trace() {}, debug() {}, status() {}, send() {}, done() {} },
    context: memoria(),
    flow: memoria(),
    global: memoria(),
    env: { get: () => undefined },
  });
  contexto.__funcao = new vm
    .Script(`(async function (msg) {\n${no.func}\n})`, { filename: `no-${nome}.js` })
    .runInContext(contexto);
  contexto.__msg = { payload, topic: 'cardioia/teste', _msgid: 'teste' };
  return vm.runInContext('__funcao(__msg)', contexto, { timeout: 1000 });
}

// ---------------------------------------------------------------- firmware (sketch.ino)

function tipoDoCampo(entreAspas, valor) {
  if (!valor.includes('%')) return 'texto'; // literal fixo, ex.: o nome do dispositivo
  if (entreAspas) return 'texto'; // "%s"
  if (valor === '%s') return 'booleano'; // %s sem aspas recebe "true"/"false"
  if (/^%l?u$/.test(valor)) return 'inteiro';
  if (/^%\.\d+f$/.test(valor)) return 'número';
  throw new Error(`firmware: especificador de formato desconhecido: ${valor}`);
}

let cacheFirmware;

// Extrai do código-fonte do firmware tudo o que faz parte do contrato com o Node-RED.
// Se o firmware mudar de forma que estas expressões deixem de achar o que procuram,
// o teste falha dizendo o que não foi encontrado (e não passa em silêncio).
export function lerFirmware() {
  if (cacheFirmware) return cacheFirmware;
  const fonte = lerTexto(CAMINHOS.firmware);

  const achar = (re, descricao) => {
    const m = fonte.match(re);
    if (!m) throw new Error(`firmware: não encontrei ${descricao}`);
    return m[1];
  };
  const texto = (nome) => achar(new RegExp(`\\b${nome}\\s*=\\s*"([^"]*)"`), nome);
  const numero = (nome) => Number(achar(new RegExp(`\\b${nome}\\s*=\\s*([0-9.]+)\\s*;`), nome));
  const trecho = (de, ate) => {
    const i = fonte.indexOf(de);
    const f = fonte.indexOf(ate, i);
    if (i < 0 || f < 0) throw new Error(`firmware: não encontrei o trecho "${de}" … "${ate}"`);
    return fonte.slice(i, f);
  };

  // Formato do snprintf de transmitirLeitura(): literais C adjacentes, concatenados.
  const transmitir = trecho('bool transmitirLeitura(const Leitura &leitura) {', '// SINCRONIZACAO DA FILA');
  const literais = transmitir.match(/sizeof\(payload\),\s*((?:"(?:[^"\\]|\\.)*"\s*)+)/);
  if (!literais) throw new Error('firmware: não encontrei o formato do snprintf em transmitirLeitura()');
  const formato = [...literais[1].matchAll(/"((?:[^"\\]|\\.)*)"/g)]
    .map((x) => x[1])
    .join('')
    .replace(/\\"/g, '"');

  const campos = [...formato.matchAll(/"([a-z_]+)":("?)([^,}"]*)\2/g)].map(([, chave, aspas, valor]) => ({
    chave,
    especificador: valor,
    literal: valor.includes('%') ? null : valor,
    tipo: tipoDoCampo(aspas === '"', valor),
  }));
  if (campos.length === 0) throw new Error('firmware: o formato do payload não tem campos reconhecíveis');

  cacheFirmware = {
    fonte,
    broker: texto('BROKER_MQTT'),
    porta: numero('PORTA_MQTT'),
    topico: texto('TOPICO_MQTT'),
    idCliente: texto('ID_CLIENTE'),
    // publish(topico, payload) em PubSubClient = QoS 0 e sem retain.
    publicaSemQosNemRetain: /mqtt\.publish\(\s*TOPICO_MQTT\s*,\s*payload\s*\)/.test(fonte),
    constantes: {
      LIMITE_BPM: numero('LIMITE_BPM'),
      LIMITE_FEBRE: numero('LIMITE_FEBRE'),
      TEMPO_SEM_MOVIMENTO_MS: numero('TEMPO_SEM_MOVIMENTO_MS'),
      ALERTA_BPM: numero('ALERTA_BPM'),
      ALERTA_FEBRE: numero('ALERTA_FEBRE'),
      ALERTA_SEM_MOVIMENTO: numero('ALERTA_SEM_MOVIMENTO'),
    },
    formato,
    campos,
    estadosMovimento: [
      ...trecho('const char* nomeMovimento', 'bool iniciarMPU').matchAll(/return\s+"([a-z]+)"\s*;/g),
    ].map((x) => x[1]),
    calcularAlertas: trecho('uint8_t calcularAlertas()', 'void descreverAlertas'),
  };
  return cacheFirmware;
}

// Valores de uma leitura em repouso, sem alertas (a mesma do exemplo do contrato).
const PADRAO = {
  dispositivo: 'cardioia-esp32-01',
  id: 1,
  timestamp_ms: 2000,
  temperatura: 24.0,
  umidade: 40.0,
  temp_corporal: 36.5,
  temp_corporal_valida: true,
  bpm: 0.0,
  bpm_valido: false,
  movimento: 'aguardando',
  aceleracao_g: 1.0,
  alertas_locais: 0,
};

// Monta o texto JSON de uma leitura formatando EXATAMENTE como o snprintf do firmware
// (mesma ordem de campos, mesmas casas decimais, booleanos como true/false). O formato vem
// do próprio sketch.ino: se o firmware ganhar um campo, esta função passa a exigir um valor
// padrão para ele, e o teste acusa a divergência.
export function montarPayloadFirmware(sobrescritas = {}) {
  const fw = lerFirmware();
  const valores = { ...PADRAO, ...sobrescritas };

  const semPadrao = fw.campos.filter((c) => !(c.chave in valores)).map((c) => c.chave);
  if (semPadrao.length) throw new Error(`o firmware publica campos sem valor padrão no teste: ${semPadrao.join(', ')}`);
  const desconhecidos = Object.keys(sobrescritas).filter((k) => !fw.campos.some((c) => c.chave === k));
  if (desconhecidos.length) throw new Error(`campos que o firmware não publica: ${desconhecidos.join(', ')}`);

  const fila = fw.campos.filter((c) => c.literal === null).map((c) => valores[c.chave]);
  let i = 0;
  return fw.formato.replace(/%(?:\.(\d+)f|lu|u|s)/g, (_, casas) => {
    const v = fila[i++];
    if (casas !== undefined) return Number(v).toFixed(Number(casas));
    if (typeof v === 'boolean') return v ? 'true' : 'false';
    if (typeof v === 'number') return String(Math.trunc(v));
    return String(v);
  });
}

// ---------------------------------------------------------------- documentos Markdown

// Lê a primeira tabela depois do título que contém `titulo`. Cada linha vira um objeto
// { nomeDaColuna: conteúdoDaCélula }. Células que são só código (`assim`) perdem os acentos graves.
export function lerTabela(md, titulo) {
  const linhas = md.split('\n');
  const eTitulo = (l) => /^#{1,6}\s/.test(l);
  const i = linhas.findIndex((l) => eTitulo(l) && l.includes(titulo));
  if (i < 0) throw new Error(`título não encontrado no documento: "${titulo}"`);

  let j = i + 1;
  while (j < linhas.length && !linhas[j].trim().startsWith('|')) {
    if (eTitulo(linhas[j])) throw new Error(`não há tabela logo abaixo do título "${titulo}"`);
    j++;
  }
  const bloco = [];
  for (; j < linhas.length && linhas[j].trim().startsWith('|'); j++) bloco.push(linhas[j].trim());

  const celulas = (linha) =>
    linha
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((c) => c.trim().replace(/^`([^`]+)`$/, '$1'));
  const [cabecalho, , ...corpo] = bloco.map(celulas); // a 2ª linha é o separador |---|
  return corpo.map((cel) => Object.fromEntries(cabecalho.map((h, k) => [h, cel[k]])));
}

// Todos os blocos ```json do documento, já convertidos em objetos.
export function blocosJson(md) {
  return [...md.matchAll(/```json\n([\s\S]*?)\n```/g)].map((m) => JSON.parse(m[1]));
}

// Remove a marcação (negrito e citação) para comparar o texto corrido de avisos.
export function semMarcacao(md) {
  return md.replace(/[*>]/g, '').replace(/\s+/g, ' ');
}
