# fet

A tiny switch-level FET circuit playground in a single HTML page. Draw
transistors, pullups, grounds, buttons and wires on an infinite grid;
the embedded simulator recomputes node states live (grey = floating,
red = high, black = low; oscillating nets that never settle get an
orange halo). Enough to build and play with a flip-flop.

Use it at https://lukacslacko.github.io/fet/ or just open `index.html`
locally — everything (UI and simulator) is embedded in that one file,
no server and no dependencies.

The circuit is kept compressed and encoded in the URL's `?c=` parameter
on every change, so the address bar is always a shareable save of the
current work.

## Cards editor

https://lukacslacko.github.io/fet/cards.html (`cards.html`) is a bigger
editor built on the same simulator: circuits are organized into named
**cards** with external **pins** (`e`; enter cycles a pin's drive
between float/high/low for testing). A card can be placed inside
another card (`c` opens a picker; circular dependencies are refused)
and appears as a bordered box showing its name and pin names, with a
wire stub below each pin to build on — so a 4-bit register can be built
out of D-latch cards. State (all cards) lives in browser storage and
can be exported/imported as JSON with `j`. The simple editor above
stays as-is as a playground.

Each card can carry a test (`t` opens the test panel): one column per
pin, one row per step. A cell is either blank (don't drive, don't
care), `h`/`l` (drive the pin high/low) or `1`/`0` (expect the pin's
net high/low). Run/Step/Restart execute the rows in order — node
states persist between rows, so latches can be clocked and then read —
and the run stops on the failing row.

An LED (`o`, cards editor only) is a pullup with an LED in series:
supply, 1k, then the LED down to the square below. It lights when
that node is pulled low — put it on top of a transistor whose source
goes to ground, and it shines while the gate is high. It counts as a
pullup for the logic; in the physical sim its diode is exponential, so
it passes about 2.7 mA into a low node and lets an undriven node under
it float up to about 3.6 V.

### PCB and schematic export

The **PCB…** button downloads the current card for EasyEDA (File ›
Open › KiCad) or KiCad, either as a board or as a schematic. The
**PCB** is a KiCad 5 board file (`.kicad_pcb`): every part is placed
in a grid mirroring the card (empty rows and columns collapsed) with
every net assigned, but nothing is routed — route or autoroute there,
then order. The **schematic** is a KiCad 5 schematic drawn square for
square like the card, saved as two files, the sheet (`CARD.sch`) and
its symbols (`CARD-cache.lib`); select both in EasyEDA's import
dialog, then lay out the PCB from it as you like. Parts are 2N7002
transistors in SOT-23, 10k chip resistors, a 1k from VDD plus a chip
LED per LED pullup (0603 or 0805, selectable), and 6×6 mm tactile
switches for buttons, with the same references, values and footprint
names in both files. The card's pins come out on a single-row 2.54 mm
header J1: GND, VDD, then the pins in their canonical order. Cards
used inside the card are either inlined (on the board their parts
boxed and labelled on the silkscreen, on the schematic drawn as their
own block joined to the instance by `CARD1/PIN` labels) or each
becomes a matching single-row socket — GND, VDD, that card's pins —
that the card's own board plugs onto.

## Keys

Point at a square and press:

- `p` pullup, `g` ground, `l`/`r` left/right facing transistor
- `w`/`a`/`s`/`d` toggle a wire arm to the top/left/bottom/right edge
- `x` crossing (wires cross without connecting), `b` button
- `o` LED (cards editor)
- `enter` flip the button under the mouse, `space` clear the square
- `n` name the hovered wire's net; nets with equal names are connected
- `j` JSON dialog to export/import the circuit
- arrows scroll, `+`/`-` zoom

## The simulator

Each settle step samples conduction (transistor gates, button
positions) from the current node states, merges nodes connected through
conducting channels, and recomputes every node from scratch: a group is
low if it touches a ground, else high if it touches a pullup, else
floating. Steps repeat until nothing changes; a symmetric latch with no
tie-breaker oscillates forever and is reported as unsettled — like real
hardware, it needs one set/reset pulse. Node states persist across
button presses (the circuit is only rebuilt when the wiring changes),
which is what gives a flip-flop its memory.
