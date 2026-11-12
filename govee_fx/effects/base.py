"""Effect base class.

To make a new animation: subclass Effect, declare `params`, implement
`update()`, and decorate with @register. The UI builds its controls from
`params`, so no frontend work is needed.
"""
from dataclasses import dataclass, field

REGISTRY = {}


@dataclass
class Param:
    key: str
    label: str
    default: float | str
    min: float = 0.0
    max: float = 1.0
    step: float = 0.01
    choices: list = field(default_factory=list)  # non-empty => dropdown

    def to_dict(self):
        d = {"key": self.key, "label": self.label, "default": self.default}
        if self.choices:
            d.update(type="choice", choices=self.choices)
        else:
            d.update(type="range", min=self.min, max=self.max, step=self.step)
        return d

    def clean(self, value):
        if self.choices:
            return value if value in self.choices else self.default
        try:
            return max(self.min, min(self.max, float(value)))
        except (TypeError, ValueError):
            return self.default


class Effect:
    name = "base"
    label = "Base"
    params: list[Param] = []

    def __init__(self, width: int, height: int):
        self.w, self.h = width, height

    def update(self, dt: float, p: dict):
        """Advance by dt seconds. Return frame: h rows (row 0 = TOP) of w (r,g,b) tuples."""
        raise NotImplementedError

    @classmethod
    def defaults(cls):
        return {p.key: p.default for p in cls.params}

    @classmethod
    def schema(cls):
        return {"name": cls.name, "label": cls.label, "params": [p.to_dict() for p in cls.params]}


def register(cls):
    REGISTRY[cls.name] = cls
    return cls
