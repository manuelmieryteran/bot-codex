"""Network-incapable sink for modular submit effects observed in shadow mode."""

from dataclasses import dataclass

from bot_spx.execution.dispatch_models import DispatchEffect


@dataclass(frozen=True)
class ShadowSubmitRecord:
    kind: str
    payload: dict[str, object]


class NullOrderSubmitPort:
    """Record submit effects as data; never execute or delegate them."""

    def __init__(self) -> None:
        self.records: list[ShadowSubmitRecord] = []

    def record(self, effect: DispatchEffect) -> ShadowSubmitRecord:
        if effect.kind != "SUBMIT_ORDER" or effect.payload is None:
            raise ValueError("NULL SUBMIT PORT REQUIRES SUBMIT_ORDER EFFECT")
        record = ShadowSubmitRecord(effect.kind, dict(effect.payload))
        self.records.append(record)
        return record
