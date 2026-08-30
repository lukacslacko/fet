"""Switch-level circuit simulator, derived-state version.

The hand-written original is preserved in sim_handwritten.py. That
version patched node states incrementally, element by element, which
made results depend on element order and let other gates observe
transient wrong values (fatal for feedback circuits like a flip-flop).

Here each Circuit.settle() call is one synchronous update step: it
samples conduction (transistor gates, button positions) from the states
the nodes have on entry, then recomputes every node's state from
scratch. Nodes joined by conducting channels form a group; a group is
LOW if it touches a ground, else HIGH if it touches a pullup (grounds
beat pullups by construction), else FLOAT. There is no float-on-open
bookkeeping and no order dependence; a latch holds its state because
the side whose transistor still conducts keeps its group grounded.

Differences from the hand-written model: no body diode (a channel
conducts exactly when its gate is HIGH), and an undriven group is FLOAT
rather than remembering its charge.

A perfectly symmetric feedback circuit with nothing to break the tie
(e.g. a freshly powered flip-flop, all nodes floating) oscillates
between its two stable states forever and never settles -- like real
hardware, it needs one set/reset pulse. The caller's iteration cap
should treat this as "did not settle".
"""

from dataclasses import dataclass
from enum import Enum


class State(Enum):
    LOW = 0
    HIGH = 1
    FLOAT = 2


@dataclass
class Node:
    state: State

    def __str__(self) -> str:
        return f"node {id(self)} in state {self.state}"


@dataclass
class Transistor:
    source: Node
    gate: Node
    drain: Node

    def __str__(self) -> str:
        return (f"transistor {id(self)} with source={self.source}, "
                f"gate={self.gate}, drain={self.drain}")


@dataclass
class Pullup:
    node: Node

    def __str__(self) -> str:
        return f"pullup {id(self)} node={self.node}"


@dataclass
class Ground:
    node: Node

    def __str__(self) -> str:
        return f"ground {id(self)} node={self.node}"


@dataclass
class Button:
    up: Node
    down: Node
    pressed: bool

    def __str__(self) -> str:
        return (f"button {id(self)} pressed={self.pressed} "
                f"up={self.up} down={self.down}")


@dataclass
class Circuit:
    transistors: list[Transistor]
    pullups: list[Pullup]
    grounds: list[Ground]
    buttons: list[Button]

    def __str__(self) -> str:
        return "\n".join(
            str(thing)
            for things in [self.transistors, self.pullups,
                           self.grounds, self.buttons]
            for thing in things)

    def settle(self) -> bool:
        """One synchronous update step; True when nothing changed.

        Call repeatedly until it returns True. A circuit that never
        settles is oscillating (a ring, or a symmetric latch with no
        tie-breaker) and should be cut off by an iteration cap.
        """
        nodes: dict[int, Node] = {}
        for t in self.transistors:
            for n in (t.source, t.gate, t.drain):
                nodes[id(n)] = n
        for p in self.pullups:
            nodes[id(p.node)] = p.node
        for g in self.grounds:
            nodes[id(g.node)] = g.node
        for b in self.buttons:
            nodes[id(b.up)] = b.up
            nodes[id(b.down)] = b.down

        # Union-find over nodes, merging across conducting channels.
        parent = {i: i for i in nodes}

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(a: Node, b: Node) -> None:
            parent[find(id(a))] = find(id(b))

        # Sample conduction from the entry states, before any rewrite.
        for t in self.transistors:
            if t.gate.state == State.HIGH:
                union(t.source, t.drain)
        for b in self.buttons:
            if b.pressed:
                union(b.up, b.down)

        grounded = {find(id(g.node)) for g in self.grounds}
        pulled_up = {find(id(p.node)) for p in self.pullups}

        changed = False
        for i, node in nodes.items():
            root = find(i)
            if root in grounded:
                new = State.LOW
            elif root in pulled_up:
                new = State.HIGH
            else:
                new = State.FLOAT
            if node.state != new:
                node.state = new
                changed = True
        return not changed
