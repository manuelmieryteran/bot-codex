"""Pure interpretation of legacy dispatch results into execution state."""

from dataclasses import replace

from bot_spx.execution.dispatch_models import ExecutionState


def post_dispatch_transition(state, dispatch_result, dispatch_id):
    dispatch_status = dispatch_result.get("status", "UNKNOWN")
    dispatch_reason = dispatch_result.get("reason", "NO DISPATCH REASON")
    new_state = replace(
        state,
        dispatch_status=dispatch_status,
        dispatch_reason=dispatch_reason,
        dispatch_id=None if dispatch_status == "IDLE" else dispatch_id,
    )
    broker_response = dispatch_result.get("broker_response")

    if dispatch_status == "SUBMITTED":
        new_state = replace(
            new_state,
            broker_order_id=None,
            broker_order_status="SUBMITTED",
            broker_order_state="OPEN",
            broker_order_status_description="PENDING BROKER STATUS",
        )

        if isinstance(broker_response, dict):
            orders = broker_response.get("Orders")

            if isinstance(orders, list) and orders:
                first_order = orders[0]

                if isinstance(first_order, dict):
                    new_state = replace(
                        new_state,
                        broker_order_id=first_order.get("OrderID"),
                        broker_order_status=first_order.get(
                            "Status",
                            first_order.get("OrderStatus", "SUBMITTED"),
                        ),
                    )
            else:
                new_state = replace(
                    new_state,
                    broker_order_id=broker_response.get("OrderID"),
                    broker_order_status=broker_response.get(
                        "Status",
                        broker_response.get("OrderStatus", "SUBMITTED"),
                    ),
                )

    elif dispatch_status == "SUBMIT_FAILED" and str(dispatch_reason).startswith(
        "ORDER SUBMISSION STATUS UNKNOWN:"
    ):
        new_state = replace(
            new_state,
            broker_order_id=None,
            broker_order_status="UNKNOWN",
            broker_order_status_description=dispatch_reason,
            broker_order_state="UNKNOWN",
        )

    return new_state
