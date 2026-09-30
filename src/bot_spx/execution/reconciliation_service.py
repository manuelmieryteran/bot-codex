"""Broker reconciliation orchestration through an explicit lookup port."""

from dataclasses import dataclass

from bot_spx.execution.broker_lookup import BrokerLookupPort
from bot_spx.execution.dispatch_models import ExecutionState
from bot_spx.execution.position_reconciliation import (
    update_broker_reconciliation_state,
)


@dataclass(frozen=True)
class ReconciliationRefresh:
    state: ExecutionState
    result: tuple[bool, str]


def refresh_broker_reconciliation(state, broker_lookup: BrokerLookupPort):
    account_id, account_reason = broker_lookup.get_primary_account_id()

    if not account_id:
        new_state = update_broker_reconciliation_state(
            state,
            None,
            {
                "ok": False,
                "reason": account_reason,
                "position": None,
            },
        )
        return ReconciliationRefresh(
            new_state,
            (
                new_state.position_reconciliation_ok,
                new_state.position_reconciliation_reason,
            ),
        )

    broker_lookup_result = broker_lookup.get_es_position(account_id)
    new_state = update_broker_reconciliation_state(
        state,
        account_id,
        broker_lookup_result,
    )
    return ReconciliationRefresh(
        new_state,
        (
            new_state.position_reconciliation_ok,
            new_state.position_reconciliation_reason,
        ),
    )
