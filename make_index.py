"""Generate index.html, the serverless single-page version of the UI.

Takes the page from ui.PAGE and replaces the server round-trip with an
embedded JavaScript port of sim.py's engine and ui.py's circuit
builder, so the result is one static file that can be hosted anywhere
(e.g. GitHub Pages). Run `python3 make_index.py` after changing ui.py
or sim.py and commit the regenerated index.html.
"""

import ui

SERVER_SYNC = """// Send the grid to the server, which builds the sim circuit and settles
// it; recolor the wires from the node states that come back.
async function sync() {
  updateUrl();
  const seq = ++syncSeq;
  let result;
  try {
    const resp = await fetch('/sim', {method: 'POST',
                                      body: JSON.stringify({cells: Object.fromEntries(cells)})});
    result = await resp.json();
  } catch (err) {
    status.textContent = 'Sim request failed: ' + err;
    return;
  }
  if (seq !== syncSeq) return;
  simStates = result.states;
  simUnsettled = result.unsettled || null;
  if (result.error) status.textContent = 'Sim error: ' + result.error;
  else if (!result.settled) status.textContent = 'Warning: circuit did not settle.';
  else status.textContent = '';
  redraw();
}"""

LOCAL_SIM = """// ---------- Simulator: JavaScript port of sim.py and the circuit
// builder from ui.py, so the page runs without a server. ----------
const SIM_MAX_ITERATIONS = 2000;

function cellPortsOf(cell) {
  if (!cell) return [];
  if (typeof cell === 'object') return 'nwes'.split('').filter(d => cell[d]);
  return {'pullup': ['s'], 'ground': ['n'],
          'left': ['n', 's', 'w'], 'right': ['n', 's', 'e'],
          'cross': ['n', 's', 'w', 'e'],
          'btn-open': ['n', 's'], 'btn-closed': ['n', 's']}[cell];
}

// Union-find over cell edge ports; touching ports of adjacent cells
// share a node, as do ports joined inside a cell and same-named nets.
function buildCircuit() {
  const parent = new Map();
  const find = p => {
    while (parent.get(p) !== p) {
      parent.set(p, parent.get(parent.get(p)));
      p = parent.get(p);
    }
    return p;
  };
  const union = (a, b) => parent.set(find(a), find(b));

  for (const [key, cell] of cells) {
    for (const d of cellPortsOf(cell)) parent.set(key + ',' + d, key + ',' + d);
  }
  for (const [key, cell] of cells) {
    const [r, c] = key.split(',').map(Number);
    const ports = cellPortsOf(cell);
    if (typeof cell === 'object') {
      for (let i = 1; i < ports.length; i++) {
        union(key + ',' + ports[0], key + ',' + ports[i]);
      }
    } else if (cell === 'cross') {
      union(key + ',n', key + ',s');
      union(key + ',w', key + ',e');
    }
    const east = r + ',' + (c + 1) + ',w', south = (r + 1) + ',' + c + ',n';
    if (ports.includes('e') && parent.has(east)) union(key + ',e', east);
    if (ports.includes('s') && parent.has(south)) union(key + ',s', south);
  }
  const named = new Map();
  for (const [key, cell] of cells) {
    if (typeof cell === 'object' && cell.name) {
      const anchor = key + ',' + cellPortsOf(cell)[0];
      if (named.has(cell.name)) union(named.get(cell.name), anchor);
      else named.set(cell.name, anchor);
    }
  }

  const rootNodes = new Map();
  const portNodes = new Map();
  for (const p of parent.keys()) {
    const root = find(p);
    if (!rootNodes.has(root)) rootNodes.set(root, {state: 'FLOAT'});
    portNodes.set(p, rootNodes.get(root));
  }

  const circuit = {transistors: [], pullups: [], grounds: [], buttons: []};
  const buttonsByCell = new Map();
  for (const [key, cell] of cells) {
    if (cell === 'pullup') {
      circuit.pullups.push({node: portNodes.get(key + ',s')});
    } else if (cell === 'ground') {
      circuit.grounds.push({node: portNodes.get(key + ',n')});
    } else if (cell === 'left' || cell === 'right') {
      circuit.transistors.push({
        source: portNodes.get(key + ',s'),
        gate: portNodes.get(key + ',' + (cell === 'left' ? 'w' : 'e')),
        drain: portNodes.get(key + ',n')});
    } else if (cell === 'btn-open' || cell === 'btn-closed') {
      const button = {up: portNodes.get(key + ',n'),
                      down: portNodes.get(key + ',s'),
                      pressed: cell === 'btn-closed'};
      circuit.buttons.push(button);
      buttonsByCell.set(key, button);
    }
  }
  return {circuit, portNodes, buttonsByCell};
}

// One synchronous update step; true when nothing changed. Conduction is
// sampled from the entry states, then every node is recomputed: nodes
// joined by conducting channels form a group, LOW if it touches a
// ground, else HIGH if it touches a pullup, else FLOAT.
function settleStep(circuit) {
  const nodes = new Set();
  for (const t of circuit.transistors) {
    nodes.add(t.source); nodes.add(t.gate); nodes.add(t.drain);
  }
  for (const p of circuit.pullups) nodes.add(p.node);
  for (const g of circuit.grounds) nodes.add(g.node);
  for (const b of circuit.buttons) { nodes.add(b.up); nodes.add(b.down); }

  const parent = new Map();
  for (const n of nodes) parent.set(n, n);
  const find = n => {
    while (parent.get(n) !== n) {
      parent.set(n, parent.get(parent.get(n)));
      n = parent.get(n);
    }
    return n;
  };
  const union = (a, b) => parent.set(find(a), find(b));

  for (const t of circuit.transistors) if (t.gate.state === 'HIGH') union(t.source, t.drain);
  for (const b of circuit.buttons) if (b.pressed) union(b.up, b.down);

  const grounded = new Set(circuit.grounds.map(g => find(g.node)));
  const pulledUp = new Set(circuit.pullups.map(p => find(p.node)));

  let changed = false;
  for (const n of nodes) {
    const root = find(n);
    const state = grounded.has(root) ? 'LOW' : pulledUp.has(root) ? 'HIGH' : 'FLOAT';
    if (n.state !== state) { n.state = state; changed = true; }
  }
  return !changed;
}

// Grid content with button open/closed collapsed away: edits that only
// flip buttons reuse the circuit, so a flip-flop keeps its memory.
function topologyKey() {
  const entries = [...cells.entries()].map(([key, cell]) => {
    if (typeof cell === 'object') {
      return [key, 'wire:' + 'nwes'.split('').filter(d => cell[d]).join('') +
                   ':' + (cell.name || '')];
    }
    if (cell === 'btn-open' || cell === 'btn-closed') return [key, 'button'];
    return [key, cell];
  });
  entries.sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
  return JSON.stringify(entries);
}

let cachedSim = null;   // {key, circuit, portNodes, buttonsByCell}

function simulate() {
  const key = topologyKey();
  if (!cachedSim || cachedSim.key !== key) cachedSim = {key, ...buildCircuit()};
  for (const [cellKey, cell] of cells) {
    if (cell === 'btn-open' || cell === 'btn-closed') {
      cachedSim.buttonsByCell.get(cellKey).pressed = cell === 'btn-closed';
    }
  }
  let settled = false, error = null;
  try {
    for (let i = 0; i < SIM_MAX_ITERATIONS; i++) {
      if (settleStep(cachedSim.circuit)) { settled = true; break; }
    }
  } catch (err) {
    error = String(err);
  }
  console.log('settled=' + settled + ' error=' + error, cachedSim.circuit);
  // When the circuit oscillates, find the nets doing it: run a few
  // more steps and record every port whose node keeps changing.
  const unsettled = {};
  if (!settled && !error) {
    const prev = new Map();
    for (const [p, n] of cachedSim.portNodes) prev.set(p, n.state);
    for (let i = 0; i < 4; i++) {
      settleStep(cachedSim.circuit);
      for (const [p, n] of cachedSim.portNodes) {
        if (n.state !== prev.get(p)) {
          const cut = p.lastIndexOf(',');
          const cellKey = p.slice(0, cut);
          if (!unsettled[cellKey]) unsettled[cellKey] = {};
          unsettled[cellKey][p.slice(cut + 1)] = true;
          prev.set(p, n.state);
        }
      }
    }
  }
  const states = {};
  for (const [cellKey, cell] of cells) {
    const st = {};
    for (const d of cellPortsOf(cell)) {
      st[d] = cachedSim.portNodes.get(cellKey + ',' + d).state;
    }
    states[cellKey] = st;
  }
  return {states, settled, error, unsettled};
}

// Settle the circuit locally, recolor the wires, refresh the URL.
function sync() {
  updateUrl();
  const result = simulate();
  simStates = result.states;
  simUnsettled = result.unsettled || null;
  if (result.error) status.textContent = 'Sim error: ' + result.error;
  else if (!result.settled) status.textContent = 'Warning: circuit did not settle.';
  else status.textContent = '';
  redraw();
}"""

SYNC_SEQ_LINE = "let syncSeq = 0;       // drop out-of-order sim responses\n"


def main():
    page = ui.PAGE
    assert SERVER_SYNC in page, "server sync block not found; update make_index.py"
    assert SYNC_SEQ_LINE in page, "syncSeq line not found; update make_index.py"
    page = page.replace(SERVER_SYNC, LOCAL_SIM)
    page = page.replace(SYNC_SEQ_LINE, "")
    with open("index.html", "w") as f:
        f.write(page)
    print(f"wrote index.html ({len(page)} bytes)")


if __name__ == "__main__":
    main()
