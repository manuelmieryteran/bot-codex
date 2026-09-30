"""TradeStation broker lookup adapter using only an injected transport port."""

from bot_spx.execution.broker_transport import (
    BrokerTransportError,
    BrokerTransportPort,
)


class TradeStationBrokerLookupAdapter:
    def __init__(self, transport: BrokerTransportPort, symbol: str) -> None:
        self._transport = transport
        self._symbol = symbol

    def _get_accounts(self):
        try:
            response = self._transport.request(
                "GET",
                "/brokerage/accounts",
                timeout=10,
            )
        except BrokerTransportError as exc:
            return {
                "ok": False,
                "status_code": None,
                "reason": f"POSITION REQUEST FAILED: {type(exc).__name__}",
                "positions": [],
            }

        if response.status_code != 200:
            return {
                "ok": False,
                "status_code": response.status_code,
                "reason": response.text,
                "accounts": [],
            }

        try:
            data = response.json()
        except ValueError:
            return {
                "ok": False,
                "status_code": response.status_code,
                "reason": "POSITION RESPONSE INVALID JSON",
                "positions": [],
            }

        return {
            "ok": True,
            "status_code": response.status_code,
            "reason": "ACCOUNTS RETRIEVED",
            "accounts": data.get("Accounts", []),
        }

    def get_primary_account_id(self):
        result = self._get_accounts()

        if not result.get("ok"):
            return None, result.get("reason", "ACCOUNT LOOKUP FAILED")

        accounts = result.get("accounts", [])
        if not accounts:
            return None, "NO TRADESTATION ACCOUNTS"

        for account in accounts:
            if (
                account.get("AccountType") == "Futures"
                and account.get("Status") == "Active"
            ):
                account_id = account.get("AccountID")
                if account_id:
                    return account_id, "ACTIVE FUTURES ACCOUNT AVAILABLE"

        return None, "NO ACTIVE FUTURES ACCOUNT"

    def _get_positions(self, account_id):
        if not account_id:
            return {
                "ok": False,
                "status_code": None,
                "reason": "ACCOUNT ID NOT AVAILABLE",
                "positions": [],
            }

        try:
            response = self._transport.request(
                "GET",
                f"/brokerage/accounts/{account_id}/positions",
                timeout=10,
            )
        except BrokerTransportError as exc:
            return {
                "ok": False,
                "status_code": None,
                "reason": f"POSITION REQUEST FAILED: {type(exc).__name__}",
                "positions": [],
            }

        if response.status_code != 200:
            return {
                "ok": False,
                "status_code": response.status_code,
                "reason": response.text,
                "positions": [],
            }

        try:
            data = response.json()
        except ValueError:
            return {
                "ok": False,
                "status_code": response.status_code,
                "reason": "POSITION RESPONSE INVALID JSON",
                "positions": [],
            }

        return {
            "ok": True,
            "status_code": response.status_code,
            "reason": "POSITIONS RETRIEVED",
            "positions": data.get("Positions", []),
        }

    def get_es_position(self, account_id):
        result = self._get_positions(account_id)

        if not result.get("ok"):
            return {
                "ok": False,
                "reason": result.get("reason", "POSITION LOOKUP FAILED"),
                "position": None,
            }

        positions = result.get("positions", [])
        for position in positions:
            symbol = str(position.get("Symbol", "")).upper()
            if symbol == self._symbol.upper():
                return {
                    "ok": True,
                    "reason": "ES POSITION FOUND",
                    "position": position,
                }

        return {
            "ok": True,
            "reason": "ES POSITION NOT FOUND",
            "position": None,
        }
