"""Provider-neutral, in-memory historical adaptation with a temporal firewall.

This module deliberately contains no loader, transport, authentication, or runtime
entry point.  A caller must construct the immutable observations in memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


def _frozen(values: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return MappingProxyType(dict(values or {}))


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _utc(value: datetime) -> datetime:
    """Normalize before comparison; same-zone datetimes otherwise ignore DST fold."""
    return value.astimezone(timezone.utc)


class HistoricalLookaheadError(ValueError):
    """A value not known at replay time attempted to cross the firewall."""


class HistoricalContractError(ValueError):
    """Malformed, incomplete, duplicated, or inconsistently ordered input."""


class DataQuality(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    MISSING = "MISSING"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    FUTURE = "FUTURE"
    INCOMPLETE = "INCOMPLETE"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Provenance:
    source: str
    source_time: datetime
    available_time: datetime
    transformation: str = "raw"
    input_identifiers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _aware(self.source_time, "source_time")
        _aware(self.available_time, "available_time")
        if not self.source:
            raise HistoricalContractError("provenance source is required")


@dataclass(frozen=True)
class HistoricalMarketObservation:
    identifier: str
    event_time: datetime
    available_time: datetime
    source_time: datetime
    ingestion_sequence: int
    kind: str
    values: Mapping[str, Any]
    provenance: Provenance
    bar_start: datetime | None = None
    bar_end: datetime | None = None
    bar_available_time: datetime | None = None
    is_complete: bool | None = None

    def __post_init__(self) -> None:
        for name in ("event_time", "available_time", "source_time"):
            _aware(getattr(self, name), name)
        for name in ("bar_start", "bar_end", "bar_available_time"):
            value = getattr(self, name)
            if value is not None:
                _aware(value, name)
        object.__setattr__(self, "values", _frozen(self.values))


@dataclass(frozen=True)
class HistoricalOptionsObservation:
    identifier: str
    event_time: datetime
    available_time: datetime
    source_time: datetime
    ingestion_sequence: int
    kind: str  # quote, trade, or open_interest; never a calculated greek
    values: Mapping[str, Any]
    provenance: Provenance
    oi_reference_date: date | None = None
    oi_available_time: datetime | None = None
    oi_source_semantics: str | None = None

    def __post_init__(self) -> None:
        for name in ("event_time", "available_time", "source_time"):
            _aware(getattr(self, name), name)
        if self.oi_available_time is not None:
            _aware(self.oi_available_time, "oi_available_time")
        object.__setattr__(self, "values", _frozen(self.values))
        if self.kind == "open_interest" and not all(
            (self.oi_reference_date, self.oi_available_time, self.oi_source_semantics)
        ):
            raise HistoricalContractError("open_interest requires reference, availability, and semantics")


@dataclass(frozen=True)
class HistoricalBrokerObservation:
    identifier: str
    event_time: datetime
    available_time: datetime
    source_time: datetime
    ingestion_sequence: int
    kind: str
    values: Mapping[str, Any]
    provenance: Provenance

    def __post_init__(self) -> None:
        for name in ("event_time", "available_time", "source_time"):
            _aware(getattr(self, name), name)
        object.__setattr__(self, "values", _frozen(self.values))


Observation = HistoricalMarketObservation | HistoricalOptionsObservation | HistoricalBrokerObservation


@dataclass(frozen=True)
class HistoricalDerivedValue:
    name: str
    value: Any
    computed_time: datetime
    available_time: datetime
    transformation: str
    input_identifiers: tuple[str, ...]
    input_available_times: tuple[datetime, ...]

    def __post_init__(self) -> None:
        _aware(self.computed_time, "computed_time")
        _aware(self.available_time, "available_time")
        for value in self.input_available_times:
            _aware(value, "input_available_time")
        if not self.input_identifiers or len(self.input_identifiers) != len(self.input_available_times):
            raise HistoricalContractError("derived values require paired input identifiers and availability")


@dataclass(frozen=True)
class HistoricalReplayInput:
    replay_time: datetime
    market: tuple[HistoricalMarketObservation, ...] = ()
    options: tuple[HistoricalOptionsObservation, ...] = ()
    broker: tuple[HistoricalBrokerObservation, ...] = ()
    derived: tuple[HistoricalDerivedValue, ...] = ()
    prior_state: Mapping[str, Any] = field(default_factory=_frozen)

    def __post_init__(self) -> None:
        _aware(self.replay_time, "replay_time")
        object.__setattr__(self, "prior_state", _frozen(self.prior_state))


@dataclass(frozen=True)
class DataQualityResult:
    usable: bool
    states: tuple[DataQuality, ...]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class HistoricalReplaySnapshot:
    replay_time: datetime
    market: tuple[HistoricalMarketObservation, ...]
    options: tuple[HistoricalOptionsObservation, ...]
    broker: tuple[HistoricalBrokerObservation, ...]
    derived: tuple[HistoricalDerivedValue, ...]
    prior_state: Mapping[str, Any]
    data_quality: DataQualityResult
    provenance: tuple[Provenance, ...]

    def replay_contract(self) -> Mapping[str, Any]:
        """Return the explicit boundary consumed by a temporal replay harness."""
        return _frozen({
            "replay_time": self.replay_time.isoformat(),
            "market": tuple(_frozen(o.values) for o in self.market),
            "options": tuple(_frozen(o.values) for o in self.options),
            "broker": tuple(_frozen(o.values) for o in self.broker),
            "derived": _frozen({v.name: v.value for v in self.derived}),
            "prior_state": self.prior_state,
            "usable": self.data_quality.usable,
        })


@dataclass(frozen=True)
class HistoricalAuditReport:
    rows_seen: int = 0
    rows_accepted: int = 0
    rows_rejected: int = 0
    future_rows_rejected: int = 0
    duplicates: int = 0
    conflicting_duplicates: int = 0
    out_of_order: int = 0
    incomplete_bars: int = 0
    missing_required: int = 0
    stale: int = 0
    snapshots_created: int = 0
    unusable_snapshots: int = 0


class TemporalFirewall:
    """The sole admission path for every observation and derived value."""

    def __init__(self, replay_time: datetime, *, staleness_limit: timedelta | None = None):
        _aware(replay_time, "replay_time")
        self.replay_time = replay_time
        self.staleness_limit = staleness_limit  # caller contract; never guessed here
        self._sequences: dict[int, Observation] = {}
        self._identifiers: dict[str, Observation] = {}
        self._last_key: tuple[datetime, int] | None = None

    def admit(self, row: Observation) -> DataQuality:
        if _utc(row.event_time) > _utc(self.replay_time):
            raise HistoricalLookaheadError(f"{row.identifier}: future event")
        if _utc(row.available_time) > _utc(self.replay_time):
            raise HistoricalLookaheadError(f"{row.identifier}: available after replay_time")
        if isinstance(row, HistoricalOptionsObservation) and row.kind == "open_interest":
            assert row.oi_available_time is not None
            if _utc(row.oi_available_time) > _utc(self.replay_time):
                raise HistoricalLookaheadError(f"{row.identifier}: OI not yet available")
        if isinstance(row, HistoricalMarketObservation) and row.bar_end is not None:
            if not row.is_complete or row.bar_available_time is None:
                raise HistoricalLookaheadError(f"{row.identifier}: incomplete bar")
            if _utc(row.bar_available_time) < _utc(row.bar_end):
                raise HistoricalContractError(f"{row.identifier}: bar available before bar end")
            if _utc(row.bar_end) > _utc(self.replay_time) or _utc(row.bar_available_time) > _utc(self.replay_time):
                raise HistoricalLookaheadError(f"{row.identifier}: bar close not yet available")
        key = (_utc(row.event_time), row.ingestion_sequence)
        if self._last_key is not None and key < self._last_key:
            raise HistoricalContractError(f"{row.identifier}: out-of-order observation")
        if row.ingestion_sequence in self._sequences:
            previous = self._sequences[row.ingestion_sequence]
            label = "duplicate" if previous == row else "conflicting duplicate"
            raise HistoricalContractError(f"{row.identifier}: {label} ingestion_sequence")
        if row.identifier in self._identifiers:
            previous = self._identifiers[row.identifier]
            label = "duplicate" if previous == row else "conflicting duplicate"
            raise HistoricalContractError(f"{row.identifier}: {label} identifier")
        self._sequences[row.ingestion_sequence] = row
        self._identifiers[row.identifier] = row
        self._last_key = key
        if self.staleness_limit is not None and _utc(self.replay_time) - _utc(row.available_time) > self.staleness_limit:
            return DataQuality.STALE
        return DataQuality.VALID

    def admit_derived(self, value: HistoricalDerivedValue) -> None:
        times = value.input_available_times + (value.available_time, value.computed_time)
        if any(_utc(moment) > _utc(self.replay_time) for moment in times):
            raise HistoricalLookaheadError(f"{value.name}: future derived input")
        latest_input = max((_utc(moment) for moment in value.input_available_times))
        if _utc(value.available_time) < max(latest_input, _utc(value.computed_time)):
            raise HistoricalContractError(f"{value.name}: derived availability precedes computation/input")


class HistoricalDatasetAdapter:
    """Pure adapter from already-loaded input records to validated snapshots."""

    def adapt(
        self, data: HistoricalReplayInput, *, staleness_limit: timedelta | None = None
    ) -> tuple[HistoricalReplaySnapshot, HistoricalAuditReport]:
        firewall = TemporalFirewall(data.replay_time, staleness_limit=staleness_limit)
        rows: tuple[Observation, ...] = data.market + data.options + data.broker
        report = HistoricalAuditReport(rows_seen=len(rows))
        states: list[DataQuality] = []
        accepted: list[Observation] = []
        try:
            for row in rows:
                quality = firewall.admit(row)
                states.append(quality)
                accepted.append(row)
            for value in data.derived:
                firewall.admit_derived(value)
        except (HistoricalLookaheadError, HistoricalContractError) as error:
            message = str(error)
            is_future = isinstance(error, HistoricalLookaheadError) and "incomplete bar" not in message
            report = replace(
                report,
                rows_accepted=len(accepted),
                rows_rejected=1,
                future_rows_rejected=int(is_future),
                duplicates=int("duplicate" in message and "conflicting" not in message),
                conflicting_duplicates=int("conflicting duplicate" in message),
                out_of_order=int("out-of-order" in message),
                incomplete_bars=int("incomplete bar" in message),
                unusable_snapshots=1,
            )
            error.audit_report = report
            raise
        missing = int(not data.market)
        if missing:
            states.append(DataQuality.MISSING)
        usable = not missing and DataQuality.STALE not in states
        quality = DataQualityResult(usable, tuple(dict.fromkeys(states or [DataQuality.VALID])),
                                    ("market observation required",) if missing else ())
        snapshot = HistoricalReplaySnapshot(
            data.replay_time, data.market, data.options, data.broker, data.derived,
            data.prior_state, quality, tuple(row.provenance for row in accepted),
        )
        report = replace(
            report, rows_accepted=len(accepted), missing_required=missing,
            stale=states.count(DataQuality.STALE), snapshots_created=1,
            unusable_snapshots=int(not usable),
        )
        return snapshot, report
