# fet

A tiny switch-level FET circuit playground. Draw transistors, pullups,
grounds, buttons and wires on an infinite grid in the browser; a small
Python server builds the circuit and simulates node states live (grey =
floating, red = high, black = low). Enough to build and play with a
flip-flop.

## Run

```
python3 ui.py
```

then open http://localhost:8000 (it opens automatically). No
dependencies beyond the Python standard library.

Or use the serverless single-page version, `index.html` — the same UI
with the simulator ported to JavaScript, hosted at
https://lukacslacko.github.io/fet/ (or open the file locally). It is
generated from `ui.py` by `make_index.py`; regenerate after changes.

## Keys

Point at a square and press:

- `p` pullup, `g` ground, `l`/`r` left/right facing transistor
- `w`/`a`/`s`/`d` toggle a wire arm to the top/left/bottom/right edge
- `x` crossing (wires cross without connecting), `b` button
- `enter` flip the button under the mouse, `space` clear the square
- `n` name the hovered wire's net; nets with equal names are connected
- `j` JSON dialog to export/import the circuit
- arrows scroll, `+`/`-` zoom

## Files

- `sim.py` — the simulator: each settle step samples conduction, merges
  nodes connected through conducting channels, and recomputes every
  node's state (ground beats pullup beats floating).
- `ui.py` — the web UI and the grid-to-circuit builder.
- `sim_handwritten.py` — an earlier hand-written incremental simulator,
  kept for reference.
- `make_index.py` / `index.html` — generator for and result of the
  static single-page version (JavaScript simulator embedded).
