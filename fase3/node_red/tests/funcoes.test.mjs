// Testes das regras de cada nó "function" do fluxo Node-RED (camada Fog).
// Executam o código REAL do fluxo exportado, sem Node-RED e sem rede.
// Rodar: npm test (em fase3/node_red)
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { carregarFluxo, executarFuncao, lerFirmware, montarPayloadFirmware } from './utilitarios.mjs';

const fluxo = carregarFluxo();
const firmware = lerFirmware();

// Entrega a leitura como o nó "mqtt in" (auto-detect) entrega: JSON já convertido em objeto,
// formatado exatamente como o snprintf do firmware.
const leitura = (sobrescritas = {}) => JSON.parse(montarPayloadFirmware(sobrescritas));
const rodar = (nome, payload) => executarFuncao(fluxo, nome, payload);
const alerta = async (sobrescritas) => (await rodar('Verificar Alertas', leitura(sobrescritas))).payload;

const SEM_ALERTA = 'Monitoramento sem alertas ativos';
// Tudo que o "mqtt in" pode entregar e que não é um objeto JSON (texto solto, JSON quebrado etc.).
const NAO_OBJETOS = ['texto solto', 42, true, null, undefined];

async function todosDescartam(nome) {
  for (const entrada of NAO_OBJETOS) {
    assert.equal(await rodar(nome, entrada), null, `"${nome}" deveria descartar o payload ${String(entrada)}`);
  }
}

describe('Processar BPM (gráfico de linha)', () => {
  it('repassa o BPM de uma leitura válida e nomeia a série do gráfico', async () => {
    const r = await rodar('Processar BPM', leitura({ bpm: 75.5, bpm_valido: true }));
    assert.equal(r.payload, 75.5);
    assert.equal(r.topic, 'BPM simulado');
  });

  it('descarta a leitura quando bpm_valido é false, mesmo com bpm maior que zero', async () => {
    assert.equal(await rodar('Processar BPM', leitura({ bpm: 150, bpm_valido: false })), null);
  });

  it('descarta a leitura quando bpm_valido está ausente (formato antigo)', async () => {
    assert.equal(await rodar('Processar BPM', { bpm: 80 }), null);
  });

  it('descarta bpm que não é número, mesmo marcado como válido', async () => {
    assert.equal(await rodar('Processar BPM', { bpm: '80', bpm_valido: true }), null);
  });

  it('descarta o que não é objeto JSON', () => todosDescartam('Processar BPM'));
});

describe('Processar Temperatura (gauge ambiental, DHT22)', () => {
  it('repassa a temperatura ambiental', async () => {
    const r = await rodar('Processar Temperatura', leitura({ temperatura: 24.0 }));
    assert.equal(r.payload, 24);
  });

  it('não confunde 0 °C com ausência de leitura', async () => {
    const r = await rodar('Processar Temperatura', leitura({ temperatura: 0 }));
    assert.equal(r.payload, 0);
  });

  it('descarta temperatura ausente ou que não é número', async () => {
    assert.equal(await rodar('Processar Temperatura', { umidade: 40 }), null);
    assert.equal(await rodar('Processar Temperatura', { temperatura: '24.0' }), null);
  });

  it('descarta o que não é objeto JSON', () => todosDescartam('Processar Temperatura'));
});

describe('Processar Temp. Corporal (gauge corporal, DS18B20)', () => {
  it('repassa a temperatura corporal quando o DS18B20 respondeu', async () => {
    const r = await rodar('Processar Temp. Corporal', leitura({ temp_corporal: 36.5, temp_corporal_valida: true }));
    assert.equal(r.payload, 36.5);
  });

  it('descarta a leitura quando temp_corporal_valida é false (o firmware envia 0.0 nesse caso)', async () => {
    assert.equal(await rodar('Processar Temp. Corporal', leitura({ temp_corporal: 0, temp_corporal_valida: false })), null);
  });

  it('descarta a leitura quando temp_corporal_valida está ausente (formato antigo)', async () => {
    assert.equal(await rodar('Processar Temp. Corporal', { temp_corporal: 36.5 }), null);
  });

  it('descarta temp_corporal que não é número, mesmo marcado como válido', async () => {
    assert.equal(await rodar('Processar Temp. Corporal', { temp_corporal: '36.5', temp_corporal_valida: true }), null);
  });

  it('descarta o que não é objeto JSON', () => todosDescartam('Processar Temp. Corporal'));
});

describe('Processar Movimento (texto do MPU6050)', () => {
  const textos = {
    aguardando: 'Aguardando primeiro movimento',
    ativo: 'Em movimento',
    parado: 'SEM MOVIMENTO (parado além do tempo limite)',
    indisponivel: 'Sensor de movimento indisponível',
  };

  for (const [estado, texto] of Object.entries(textos)) {
    it(`estado "${estado}" vira "${texto}" (sem aceleração, sem sufixo)`, async () => {
      const r = await rodar('Processar Movimento', { movimento: estado });
      assert.equal(r.payload, texto);
    });
  }

  it('acrescenta o módulo da aceleração com 2 casas decimais', async () => {
    const r = await rodar('Processar Movimento', leitura({ movimento: 'ativo', aceleracao_g: 1.3 }));
    assert.equal(r.payload, 'Em movimento (|a| = 1.30 g)');
  });

  it('não mostra a aceleração quando o sensor está indisponível', async () => {
    const r = await rodar('Processar Movimento', leitura({ movimento: 'indisponivel', aceleracao_g: 0 }));
    assert.equal(r.payload, 'Sensor de movimento indisponível');
  });

  it('mostra um estado desconhecido como veio (não esconde um estado novo do firmware)', async () => {
    const r = await rodar('Processar Movimento', { movimento: 'caindo', aceleracao_g: 2 });
    assert.equal(r.payload, 'caindo (|a| = 2.00 g)');
  });

  it('descarta movimento ausente ou que não é texto', async () => {
    assert.equal(await rodar('Processar Movimento', { aceleracao_g: 1 }), null);
    assert.equal(await rodar('Processar Movimento', { movimento: 2 }), null);
    await todosDescartam('Processar Movimento');
  });
});

describe('Processar Alertas Locais (máscara de bits decidida pelo ESP32)', () => {
  const esperado = {
    0: 'Nenhum',
    1: 'BPM elevado',
    2: 'Febre',
    3: 'BPM elevado | Febre',
    4: 'Sem movimento',
    5: 'BPM elevado | Sem movimento',
    6: 'Febre | Sem movimento',
    7: 'BPM elevado | Febre | Sem movimento',
  };

  for (const [mascara, texto] of Object.entries(esperado)) {
    it(`máscara ${mascara} vira "${texto}"`, async () => {
      const r = await rodar('Processar Alertas Locais', leitura({ alertas_locais: Number(mascara) }));
      assert.equal(r.payload, texto);
    });
  }

  it('ignora bits que o contrato não define (máscara 8 = nenhum alerta conhecido)', async () => {
    const r = await rodar('Processar Alertas Locais', { alertas_locais: 8 });
    assert.equal(r.payload, 'Nenhum');
  });

  it('com bit desconhecido junto de bits conhecidos, mostra só os conhecidos (máscara 15)', async () => {
    const r = await rodar('Processar Alertas Locais', { alertas_locais: 15 });
    assert.equal(r.payload, 'BPM elevado | Febre | Sem movimento');
  });

  it('descarta máscara ausente ou que não é número', async () => {
    assert.equal(await rodar('Processar Alertas Locais', { movimento: 'ativo' }), null);
    assert.equal(await rodar('Processar Alertas Locais', { alertas_locais: '7' }), null);
    await todosDescartam('Processar Alertas Locais');
  });
});

describe('Verificar Alertas (regras avaliadas pelo Fog)', () => {
  it('leitura em repouso: sem alertas', async () => {
    assert.equal(await alerta({}), SEM_ALERTA);
  });

  // ---- BPM (limite 120, comparação "maior que")
  it('BPM 119.9 válido não alerta', async () => {
    assert.equal(await alerta({ bpm: 119.9, bpm_valido: true }), SEM_ALERTA);
  });

  it('BPM 120 válido (limite exato) não alerta', async () => {
    assert.equal(await alerta({ bpm: 120, bpm_valido: true }), SEM_ALERTA);
  });

  it('BPM 120.1 válido alerta', async () => {
    assert.equal(await alerta({ bpm: 120.1, bpm_valido: true }), 'ALERTA: BPM simulado elevado');
  });

  it('BPM alto sem validade (bpm_valido false) não alerta', async () => {
    assert.equal(await alerta({ bpm: 150, bpm_valido: false }), SEM_ALERTA);
  });

  it('BPM que não é número não alerta, mesmo marcado como válido', async () => {
    const r = await rodar('Verificar Alertas', { ...leitura({ bpm_valido: true }), bpm: '130' });
    assert.equal(r.payload, SEM_ALERTA);
  });

  // ---- Febre (limite 38, DS18B20)
  it('temperatura corporal 37.9 não alerta', async () => {
    assert.equal(await alerta({ temp_corporal: 37.9 }), SEM_ALERTA);
  });

  it('temperatura corporal 38 (limite exato) não alerta', async () => {
    assert.equal(await alerta({ temp_corporal: 38.0 }), SEM_ALERTA);
  });

  it('temperatura corporal 38.1 alerta como febre', async () => {
    assert.equal(await alerta({ temp_corporal: 38.1 }), 'ALERTA: Febre (temperatura corporal elevada)');
  });

  it('temperatura corporal alta sem validade (temp_corporal_valida false) não alerta', async () => {
    assert.equal(await alerta({ temp_corporal: 39, temp_corporal_valida: false }), SEM_ALERTA);
  });

  // ---- Movimento
  it('estado "parado" alerta; os demais estados não', async () => {
    assert.equal(await alerta({ movimento: 'parado' }), 'ALERTA: Sem movimento');
    for (const estado of ['aguardando', 'ativo', 'indisponivel']) {
      assert.equal(await alerta({ movimento: estado }), SEM_ALERTA, `estado ${estado}`);
    }
  });

  // ---- Temperatura ambiental (limite 38, DHT22)
  it('temperatura ambiental 38 (limite exato) não alerta', async () => {
    assert.equal(await alerta({ temperatura: 38.0 }), SEM_ALERTA);
  });

  it('temperatura ambiental 38.1 alerta (e não é febre)', async () => {
    assert.equal(await alerta({ temperatura: 38.1 }), 'ALERTA: Temperatura ambiental elevada');
  });

  // ---- Combinações
  it('febre e temperatura ambiental juntas aparecem separadas por " | "', async () => {
    assert.equal(
      await alerta({ temp_corporal: 39, temperatura: 39 }),
      'ALERTA: Febre (temperatura corporal elevada) | Temperatura ambiental elevada',
    );
  });

  it('todos os alertas juntos, sempre na mesma ordem', async () => {
    assert.equal(
      await alerta({ temperatura: 39.5, temp_corporal: 39.2, bpm: 135, bpm_valido: true, movimento: 'parado', alertas_locais: 7 }),
      'ALERTA: BPM simulado elevado | Febre (temperatura corporal elevada) | Sem movimento | Temperatura ambiental elevada',
    );
  });

  // ---- Mensagens fora do padrão
  it('formato antigo (só temperatura, umidade, bpm e bpm_valido) é processado sem erro', async () => {
    const r = await rodar('Verificar Alertas', { temperatura: 25, umidade: 50, bpm: 75, bpm_valido: true });
    assert.equal(r.payload, SEM_ALERTA);
  });

  it('formato antigo com temperatura ambiental alta ainda alerta', async () => {
    const r = await rodar('Verificar Alertas', { temperatura: 39 });
    assert.equal(r.payload, 'ALERTA: Temperatura ambiental elevada');
  });

  it('objeto vazio não gera alerta nem erro', async () => {
    const r = await rodar('Verificar Alertas', {});
    assert.equal(r.payload, SEM_ALERTA);
  });

  it('descarta o que não é objeto JSON', () => todosDescartam('Verificar Alertas'));
});

describe('Edge × Fog: as mesmas regras dos dois lados', () => {
  it('Fog e Edge concordam em BPM, febre e sem movimento em todas as combinações de entrada', async () => {
    const { LIMITE_BPM, LIMITE_FEBRE, ALERTA_BPM, ALERTA_FEBRE, ALERTA_SEM_MOVIMENTO } = firmware.constantes;

    // Espelho de calcularAlertas() do firmware, com as constantes lidas do próprio sketch.ino.
    // O teste de contrato confere que o código C++ continua usando estas comparações.
    const mascaraDoEdge = (l) =>
      (l.bpm_valido && l.bpm > LIMITE_BPM ? ALERTA_BPM : 0) |
      (l.temp_corporal_valida && l.temp_corporal > LIMITE_FEBRE ? ALERTA_FEBRE : 0) |
      (l.movimento === 'parado' ? ALERTA_SEM_MOVIMENTO : 0);
    const mascaraDoFog = (texto) =>
      (texto.includes('BPM simulado elevado') ? ALERTA_BPM : 0) |
      (texto.includes('Febre') ? ALERTA_FEBRE : 0) |
      (texto.includes('Sem movimento') ? ALERTA_SEM_MOVIMENTO : 0);

    const divergencias = [];
    let combinacoes = 0;
    for (const bpm of [0, 119.9, 120, 120.1, 200]) {
      for (const bpm_valido of [true, false]) {
        for (const temp_corporal of [0, 37.9, 38, 38.1, 41]) {
          for (const temp_corporal_valida of [true, false]) {
            for (const movimento of firmware.estadosMovimento) {
              const entrada = leitura({ bpm, bpm_valido, temp_corporal, temp_corporal_valida, movimento });
              const fog = mascaraDoFog((await rodar('Verificar Alertas', entrada)).payload);
              const edge = mascaraDoEdge(entrada);
              combinacoes++;
              if (fog !== edge) divergencias.push({ bpm, bpm_valido, temp_corporal, temp_corporal_valida, movimento, edge, fog });
            }
          }
        }
      }
    }
    assert.equal(combinacoes, 400);
    assert.deepEqual(divergencias.slice(0, 5), [], `${divergencias.length} combinações divergem (primeiras 5 acima)`);
  });
});
