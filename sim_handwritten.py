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
        return f"transistor {id(self)} with {self.source=}, {self.gate=}, {self.drain=}"

    # We store our last handled gate state. In case our gate goes low,
    # we need to float our terminals, in case they were grounded through us.
    old_gate_state: State = State.FLOAT

    def settle(self) -> bool:
        # Body diode.
        if self.source.state == State.HIGH:
            if self.drain.state != State.HIGH:
                self.drain.state = State.HIGH
                return False
        # Otherwise we need to know our gate.    
        if self.gate.state == State.FLOAT:
            self.old_gate_state = State.FLOAT
            return False
        # If we are still closed, there's not much to do.
        if self.gate.state == State.LOW and self.old_gate_state == State.LOW:
            return True
        # If we just got closed, float our terminals, just in case they were grounded through us.
        if self.gate.state == State.LOW and self.old_gate_state != State.LOW:
            self.old_gate_state = State.LOW
            self.drain.state = State.FLOAT
            self.source.state = State.FLOAT
            return False
        # Let's now handle our gate being high.
        self.old_gate_state = self.gate.state
        # Now we are open, the two terminals should be the same.
        if {self.source.state, self.drain.state} == {State.FLOAT}:
            # Both float, we are not yet settled.
            return False
        # At least one terminal does not float.
        if self.source.state == self.drain.state:
            # We are settled.
            return True
        if self.source.state == State.FLOAT:
            self.source.state = self.drain.state
            return False
        if self.drain.state == State.FLOAT:
            self.drain.state = self.source.state
            return False
        # OK, so, now source and drain are not floating and not the same.
        # In this case the ground wins over the pullup.
        if self.source.state == State.LOW:
            self.drain.state = State.LOW
            return False
        if self.drain.state == State.LOW:
            self.source.state = State.LOW
            return False
        # I'm pretty sure we've covered all cases above.
        raise Exception("This should not be reachable.")


@dataclass
class Pullup:
    node: Node

    def __str__(self) -> str:
        return f"pullup {id(self)} {self.node=}"

@dataclass
class Ground:
    node: Node

    def __str__(self) -> str:
        return f"ground {id(self)} {self.node=}"

@dataclass
class Button:
    up: Node
    down: Node
    pressed: bool
    old_pressed: bool = False

    def __str__(self) -> str:
        return f"button {id(self)} {self.pressed=} {self.up=} {self.down=}"

    def settle(self) -> bool:
        if self.pressed:
            self.old_pressed = True
            # If something is grounded, it pulls the other down.
            if self.up.state == State.LOW:
                if self.down.state == State.LOW:
                    return True
                self.down.state = State.LOW
                return False
            if self.down.state == State.LOW:
                self.up.state = State.LOW
                return False
            # If something is pulled up, and nothing is grounded, the other is pulled up, too.
            if self.up.state == State.HIGH:
                if self.down.state == State.HIGH:
                    return True
                self.down.state = State.HIGH
                return False
            if self.down.state == State.HIGH:
                self.up.state = State.HIGH
                return False
            # Otherwise all is floating, oh well.
            return False
        # If we are not pressed, and just got unpressed, let's float the terminals.
        if self.old_pressed:
            self.up.state = State.FLOAT
            self.down.state = State.FLOAT
            self.old_pressed = self.pressed
            return False
        # Otherwise we are fine if none of our terminals float.
        return State.FLOAT not in {self.up.state, self.down.state}

@dataclass
class Circuit:
    transistors: list[Transistor]
    pullups: list[Pullup]
    grounds: list[Ground]
    buttons: list[Button]

    def __str__(self) -> str:
        return "\n".join([
            "\n".join([
                str(thing) for thing in things
            ]) for things in [self.transistors, self.pullups, self.grounds, self.buttons]
        ])

    def settle(self) -> bool:
        for ground in self.grounds:
            if ground.node.state != State.LOW:
                ground.node.state = State.LOW
                return False
        for pullup in self.pullups:
            if pullup.node.state == State.FLOAT:
                pullup.node.state = State.HIGH
                return False
        for button in self.buttons:
            result = button.settle()
            if not result:
                return False
        for transistor in self.transistors:
            result = transistor.settle()
            if not result:
                return False
        return True