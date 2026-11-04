// Testes de contrato: firmware (sketch.ino) × fluxo Node-RED × contrato (docs/contrato_mqtt.md) × documentos.
// Falham quando um lado muda e os outros ficam para trás, e dizem onde.
// Rodar: npm test (em fase3/node_red)
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {
  CAMINHOS, blocosJson, carregarFluxo, executarFuncao, lerFirmware, lerTabela, lerTexto,
  montarPayloadFirmware, noPorNome, nosFuncao, semMarcacao,
} from './utilitarios.mjs';

const fluxo = carregarFluxo();
const firmware = lerFirmware();
const docs = {
  contrato: lerTexto(CAMINHOS.contrato),
  readmeFase3: lerTexto(CAMINHOS.readmeFase3),
  readmeNodeRed: lerTexto(CAMINHOS.readmeNodeRed),
  relatorioEdge: lerTexto(CAMINHOS.relatorioEdge),
  relatorioMqtt: lerTexto(CAMINHOS.relatorioMqtt),
};
const SEM_ALERTA = 'Monitoramento sem alertas ativos';
const WIDGETS = ['ui-chart', 'ui-gauge', 'ui-text'];
const porId = new Map(fluxo.map((n) => [n.id, n]));
const quemAlimenta = (id) => fluxo.filter((n) => (n.wires ?? []).some((saida) => saida.includes(id)));
const codigo = (nome) => noPorNome(fluxo, nome).func;
// Roda "Verificar Alertas" com uma leitura no formato do firmware.
const verificarAlertas = async (sobrescritas) =>
  (await executarFuncao(fluxo, 'Verificar Alertas', JSON.parse(montarPayloadFirmware(sobrescritas)))).payload;

// ------------------------------------------------------------------------------------------

describe('Integridade do fluxo exportado', () => {
  it('todo nó tem id único', () => {
    assert.equal(porId.size, fluxo.length);
  });

  it('todo fio aponta para um nó que existe', () => {
    const quebrados = [];
    for (const no of fluxo) {
      for (const saida of no.wires ?? []) {
        for (const alvo of saida) if (!porId.has(alvo)) quebrados.push(`${no.name ?? no.id} -> ${alvo}`);
      }
    }
    assert.deepEqual(quebrados, []);
  });

  it('todo nó de fluxo pertence a uma aba que existe', () => {
    const orfaos = fluxo.filter((n) => n.z && porId.get(n.z)?.type !== 'tab').map((n) => n.name ?? n.id);
    assert.deepEqual(orfaos, []);
  });

  it('as referências de configuração existem (broker, grupo, página, base do dashboard e tema)', () => {
    const faltando = [];
    const exige = (no, campo, tipo) => {
      if (porId.get(no[campo])?.type !== tipo) faltando.push(`${no.name ?? no.id}.${campo} deveria apontar para ${tipo}`);
    };
    for (const no of fluxo) {
      if (no.type === 'mqtt in') exige(no, 'broker', 'mqtt-broker');
      if (WIDGETS.includes(no.type)) exige(no, 'group', 'ui-group');
      if (no.type === 'ui-group') exige(no, 'page', 'ui-page');
      if (no.type === 'ui-page') {
        exige(no, 'ui', 'ui-base');
        exige(no, 'theme', 'ui-theme');
      }
    }
    assert.deepEqual(faltando, []);
  });

  it('existe um único nó "mqtt in" e um único broker', () => {
    assert.equal(fluxo.filter((n) => n.type === 'mqtt in').length, 1);
    assert.equal(fluxo.filter((n) => n.type === 'mqtt-broker').length, 1);
  });

  it('todo nó function compila', () => {
    for (const no of nosFuncao(fluxo)) {
      assert.doesNotThrow(() => new vm.Script(`(async function (msg) {\n${no.func}\n})`), `nó "${no.name}"`);
    }
  });

  it('o mqtt in alimenta todas as funções e cada função alimenta ao menos um widget', () => {
    const mqttIn = fluxo.find((n) => n.type === 'mqtt in');
    for (const f of nosFuncao(fluxo)) {
      assert.ok(quemAlimenta(f.id).some((n) => n.id === mqttIn.id), `"${f.name}" não recebe do mqtt in`);
      assert.ok(f.wires.flat().some((id) => WIDGETS.includes(porId.get(id)?.type)), `"${f.name}" não alimenta nenhum widget`);
    }
  });

  it('todo widget recebe dados de uma função (nenhum widget órfão)', () => {
    const widgets = fluxo.filter((n) => WIDGETS.includes(n.type));
    assert.ok(widgets.length >= 6, 'esperava ao menos 6 widgets (gráfico, 2 gauges e 3 textos)');
    for (const w of widgets) {
      assert.ok(quemAlimenta(w.id).some((n) => n.type === 'function'), `widget "${w.name}" não recebe de nenhuma função`);
    }
  });

  it('o fluxo não guarda usuário, senha nem token', () => {
    const suspeitos = fluxo.flatMap((n) =>
      Object.keys(n)
        .filter((k) => /pass|secret|token|api_?key|credential/i.test(k))
        .map((k) => `${n.name ?? n.id}.${k}`));
    assert.deepEqual(suspeitos, []);
  });

  it('os textos do dashboard não são cortados com reticências (wrapText ligado)', () => {
    const textos = fluxo.filter((n) => n.type === 'ui-text');
    assert.ok(textos.length >= 3);
    assert.deepEqual(textos.filter((n) => n.wrapText !== true).map((n) => n.name), []);
  });

  it('a versão do Dashboard 2.0 configurada no fluxo está documentada nos READMEs', () => {
    const dashboard = fluxo.find((n) => n.type === 'global-config')?.modules?.['@flowfuse/node-red-dashboard'];
    assert.ok(dashboard, 'o fluxo não registra a versão do dashboard no nó global-config');
    for (const [nome, md] of [['README da Fase 3', docs.readmeFase3], ['README do Node-RED', docs.readmeNodeRed]]) {
      assert.ok(md.includes(dashboard), `${nome} não cita o dashboard ${dashboard}`);
    }
  });
});

// ------------------------------------------------------------------------------------------

describe('Firmware × fluxo Node-RED', () => {
  const mqttIn = fluxo.find((n) => n.type === 'mqtt in');
  const broker = fluxo.find((n) => n.type === 'mqtt-broker');

  it('mesmo broker, porta e tópico', () => {
    assert.equal(broker.broker, firmware.broker);
    assert.equal(Number(broker.port), firmware.porta);
    assert.equal(mqttIn.topic, firmware.topico);
  });

  it('o fluxo assina com QoS 0 e o firmware publica sem QoS nem retain', () => {
    assert.equal(String(mqttIn.qos), '0');
    assert.ok(firmware.publicaSemQosNemRetain, 'o firmware deixou de usar mqtt.publish(TOPICO_MQTT, payload)');
  });

  it('o fluxo só lê campos que o firmware publica', () => {
    const publicados = new Set(firmware.campos.map((c) => c.chave));
    const lidos = new Set(nosFuncao(fluxo).flatMap((n) => [...n.func.matchAll(/dados\.([a-z_]+)/g)].map((m) => m[1])));
    assert.ok(lidos.size > 0);
    assert.deepEqual([...lidos].filter((c) => !publicados.has(c)), []);
  });

  it('os limiares de BPM e de febre do fluxo são os LIMITE_* do firmware', () => {
    const fog = codigo('Verificar Alertas');
    assert.equal(Number(fog.match(/dados\.bpm\s*>\s*([0-9.]+)/)?.[1]), firmware.constantes.LIMITE_BPM);
    assert.equal(Number(fog.match(/dados\.temp_corporal\s*>\s*([0-9.]+)/)?.[1]), firmware.constantes.LIMITE_FEBRE);
  });

  it('o firmware ainda calcula os alertas com as comparações que o teste Edge × Fog espelha', () => {
    const c = firmware.calcularAlertas.replace(/\s+/g, ' ');
    assert.match(c, /bpmValidoAgora\(\) && bpm > LIMITE_BPM/);
    assert.match(c, /tempCorporalValida && tempCorporal > LIMITE_FEBRE/);
    assert.match(c, /estadoMovimento == MOV_PARADO/);
  });

  it('as máscaras que o fluxo decodifica são as constantes ALERTA_* do firmware', () => {
    const doFluxo = [...codigo('Processar Alertas Locais').matchAll(/bits\s*&\s*(\d+)\)\s*lista\.push\("([^"]+)"\)/g)]
      .map((m) => Number(m[1]))
      .sort((a, b) => a - b);
    const doFirmware = Object.entries(firmware.constantes)
      .filter(([nome]) => nome.startsWith('ALERTA_'))
      .map(([, valor]) => valor)
      .sort((a, b) => a - b);
    assert.deepEqual(doFluxo, doFirmware);
  });

  it('os estados de movimento que o fluxo conhece são os que o firmware envia', () => {
    const doFluxo = [...codigo('Processar Movimento').matchAll(/^\s*([a-z]+):\s*"/gm)].map((m) => m[1]).sort();
    assert.deepEqual(doFluxo, [...firmware.estadosMovimento].sort());
  });

  it('o alerta de "sem movimento" do fluxo usa o mesmo estado que o firmware usa para ALERTA_SEM_MOVIMENTO', () => {
    const nomeDoEnum = Object.fromEntries(
      [...firmware.fonte.matchAll(/case\s+(MOV_[A-Z]+):\s*return\s+"([a-z]+)"/g)].map((m) => [m[1], m[2]]));
    const enumDoAlerta = firmware.calcularAlertas.match(/estadoMovimento\s*==\s*(MOV_[A-Z]+)/)?.[1];
    const estadoNoFluxo = codigo('Verificar Alertas').match(/dados\.movimento\s*===\s*"([a-z]+)"/)?.[1];
    assert.ok(enumDoAlerta, 'não achei o estado de movimento que dispara ALERTA_SEM_MOVIMENTO no firmware');
    assert.ok(estadoNoFluxo, 'não achei o estado de movimento que o fluxo trata como "sem movimento"');
    assert.equal(nomeDoEnum[enumDoAlerta], estadoNoFluxo);
  });
});

// ------------------------------------------------------------------------------------------

describe('Contrato (docs/contrato_mqtt.md) × firmware × fluxo', () => {
  it('transporte: broker, porta, tópico, QoS, retain e identificador do cliente', () => {
    const t = Object.fromEntries(lerTabela(docs.contrato, 'Transporte').map((l) => [l.Item, l.Valor]));
    assert.equal(t.Broker, firmware.broker);
    assert.equal(Number(t.Porta), firmware.porta);
    assert.equal(t['Tópico'], firmware.topico);
    assert.equal(t.QoS, '0');
    assert.equal(t.Retain, 'não');
    assert.ok(firmware.publicaSemQosNemRetain);
    assert.equal(t['Identificador do cliente (ESP32)'], firmware.idCliente);
  });

  const campos = lerTabela(docs.contrato, 'Campos do payload');

  it('campos: mesma lista, ordem e tipos do snprintf do firmware', () => {
    assert.deepEqual(
      campos.map((c) => [c.Campo, c.Tipo]),
      firmware.campos.map((c) => [c.chave, c.tipo]),
    );
  });

  it('campos: cada nó lê exatamente os campos da coluna "Nós do Node-RED que usam"', () => {
    const doContrato = new Map();
    for (const c of campos) {
      const nos = c['Nós do Node-RED que usam'];
      if (nos === '—') continue;
      for (const nome of nos.split(';').map((s) => s.trim())) {
        if (!doContrato.has(nome)) doContrato.set(nome, new Set());
        doContrato.get(nome).add(c.Campo);
      }
    }
    const doFluxo = new Map(
      nosFuncao(fluxo).map((n) => [n.name, new Set([...n.func.matchAll(/dados\.([a-z_]+)/g)].map((m) => m[1]))]));
    assert.deepEqual([...doContrato.keys()].sort(), [...doFluxo.keys()].sort(), 'nós citados × nós function do fluxo');
    for (const [nome, lidos] of doFluxo) {
      assert.deepEqual([...doContrato.get(nome)].sort(), [...lidos].sort(), `campos lidos pelo nó "${nome}"`);
    }
  });

  it('alertas locais: bits, constantes do firmware e textos exibidos no dashboard', async () => {
    const linhas = lerTabela(docs.contrato, 'Alertas locais');
    const constantesDoFirmware = Object.keys(firmware.constantes).filter((n) => n.startsWith('ALERTA_')).sort();
    assert.deepEqual(linhas.map((l) => l['Constante no firmware']).sort(), constantesDoFirmware);
    for (const l of linhas) {
      const valor = Number(l.Valor);
      assert.equal(valor, 2 ** Number(l.Bit), `${l.Alerta}: o valor deve ser 2 elevado ao bit`);
      assert.equal(firmware.constantes[l['Constante no firmware']], valor, `${l.Alerta}: valor × constante do firmware`);
      const r = await executarFuncao(fluxo, 'Processar Alertas Locais', { alertas_locais: valor });
      assert.equal(r.payload, l['Texto no dashboard'], `${l.Alerta}: texto exibido`);
    }
  });

  it('estados de movimento: tabela × firmware × texto exibido no dashboard', async () => {
    const linhas = lerTabela(docs.contrato, 'Estados de movimento');
    assert.deepEqual(linhas.map((l) => l.Estado).sort(), [...firmware.estadosMovimento].sort());
    for (const l of linhas) {
      const r = await executarFuncao(fluxo, 'Processar Movimento', { movimento: l.Estado });
      assert.equal(r.payload, l['Texto no dashboard'], `estado ${l.Estado}`);
    }
  });

  it('limiares: tabela × firmware × fluxo, e o comportamento exatamente no valor-limite', async () => {
    const linhas = lerTabela(docs.contrato, 'Limiares e regras');
    const regra = Object.fromEntries(linhas.map((l) => [l.Regra, l]));

    // 1) valores da tabela × constantes do firmware
    for (const l of linhas) {
      const constante = l['Constante no firmware'];
      if (constante !== '—') {
        assert.equal(firmware.constantes[constante], Number(l.Valor), `${l.Regra}: valor × ${constante}`);
      }
    }

    // 2) valores da tabela × código do nó "Verificar Alertas"
    const fog = codigo('Verificar Alertas');
    const noFluxo = {
      'BPM elevado': /dados\.bpm\s*>\s*([0-9.]+)/,
      Febre: /dados\.temp_corporal\s*>\s*([0-9.]+)/,
      'Temperatura ambiental elevada': /dados\.temperatura\s*>\s*([0-9.]+)/,
    };
    for (const [nome, re] of Object.entries(noFluxo)) {
      assert.equal(Number(fog.match(re)?.[1]), Number(regra[nome].Valor), `${nome}: valor × código do fluxo`);
    }

    // 3) comportamento: o valor exato do limite não alerta; logo acima, alerta com o texto da tabela
    const entradas = {
      'BPM elevado': (v) => ({ bpm: v, bpm_valido: true }),
      Febre: (v) => ({ temp_corporal: v }),
      'Temperatura ambiental elevada': (v) => ({ temperatura: v }),
    };
    for (const [nome, montar] of Object.entries(entradas)) {
      const limite = Number(regra[nome].Valor);
      assert.equal(await verificarAlertas(montar(limite)), SEM_ALERTA, `${nome}: o valor exato do limite não alerta`);
      assert.equal(
        await verificarAlertas(montar(limite + 0.1)),
        `ALERTA: ${regra[nome]['Texto do alerta no dashboard']}`,
        `${nome}: acima do limite alerta`,
      );
    }
    assert.equal(
      await verificarAlertas({ movimento: 'parado' }),
      `ALERTA: ${regra['Sem movimento']['Texto do alerta no dashboard']}`,
    );

    // 4) vários alertas juntos aparecem na ordem da tabela
    const todos = await verificarAlertas({ bpm: 130, bpm_valido: true, temp_corporal: 39, temperatura: 39, movimento: 'parado' });
    assert.equal(todos, `ALERTA: ${linhas.map((l) => l['Texto do alerta no dashboard']).join(' | ')}`);
  });
});

// ------------------------------------------------------------------------------------------

describe('Documentos × firmware', () => {
  const chavesDoFirmware = firmware.campos.map((c) => c.chave);

  for (const [nome, md] of [
    ['contrato', docs.contrato],
    ['README da Fase 3', docs.readmeFase3],
    ['relatório MQTT', docs.relatorioMqtt],
  ]) {
    it(`o exemplo de payload do ${nome} tem os campos do firmware, na mesma ordem`, () => {
      const exemplo = blocosJson(md).find((b) => 'dispositivo' in b);
      assert.ok(exemplo, `não achei um exemplo de payload (bloco json) no ${nome}`);
      assert.deepEqual(Object.keys(exemplo), chavesDoFirmware);
    });
  }

  it('o exemplo de payload do contrato tem os tipos que o firmware formata', () => {
    const exemplo = blocosJson(docs.contrato).find((b) => 'dispositivo' in b);
    for (const { chave, tipo } of firmware.campos) {
      const v = exemplo[chave];
      if (tipo === 'texto') assert.equal(typeof v, 'string', chave);
      if (tipo === 'booleano') assert.equal(typeof v, 'boolean', chave);
      if (tipo === 'número') assert.equal(typeof v, 'number', chave);
      if (tipo === 'inteiro') assert.ok(Number.isInteger(v), chave);
    }
  });

  it('README, relatório e contrato citam o mesmo broker, porta e tópico do firmware', () => {
    for (const [nome, md] of Object.entries(docs)) {
      if (nome === 'relatorioEdge') continue; // o relatório da Parte 1 não trata de MQTT
      for (const esperado of [firmware.broker, String(firmware.porta), firmware.topico]) {
        assert.ok(md.includes(esperado), `${nome} não cita "${esperado}"`);
      }
    }
  });

  it('o README da Fase 3 cita os mesmos limiares do firmware', () => {
    const { LIMITE_BPM, LIMITE_FEBRE, TEMPO_SEM_MOVIMENTO_MS } = firmware.constantes;
    assert.match(docs.readmeFase3, new RegExp(`>\\s*${LIMITE_BPM}\\b`), 'limiar de BPM');
    assert.match(docs.readmeFase3, new RegExp(`>\\s*${LIMITE_FEBRE}\\s*°C`), 'limiar de febre / ambiente');
    assert.match(docs.readmeFase3, new RegExp(`\\b${TEMPO_SEM_MOVIMENTO_MS / 1000} s\\b`), 'tempo sem movimento');
  });

  it('o link do projeto no Wokwi é o mesmo em todos os documentos', () => {
    const arquivos = {
      'README da raiz': CAMINHOS.readmeRaiz,
      'README da Fase 3': CAMINHOS.readmeFase3,
      'relatório Edge': CAMINHOS.relatorioEdge,
      'relatório MQTT': CAMINHOS.relatorioMqtt,
      'roteiro de teste': CAMINHOS.roteiro,
    };
    const ids = new Map();
    for (const [nome, caminho] of Object.entries(arquivos)) {
      for (const m of lerTexto(caminho).matchAll(/wokwi\.com\/projects\/(\d+)/g)) {
        ids.set(m[1], [...(ids.get(m[1]) ?? []), nome]);
      }
    }
    assert.equal(ids.size, 1, `há mais de um projeto do Wokwi citado: ${JSON.stringify([...ids])}`);
  });

  it('os documentos da Fase 3 trazem o aviso clínico obrigatório (CLAUDE.md §3)', () => {
    const aviso =
      'AVISO CLÍNICO: Este sistema é um protótipo acadêmico e NÃO substitui avaliação médica. ' +
      'Supervisionado por Dra. Fernanda Fassina (CRM-SP 169944).';
    for (const [nome, md] of Object.entries(docs)) {
      assert.ok(semMarcacao(md).includes(aviso), `${nome} sem o aviso clínico`);
    }
  });
});
