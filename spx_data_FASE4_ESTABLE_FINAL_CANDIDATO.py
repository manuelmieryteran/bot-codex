from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import os
import pandas as pd
import requests
import json
import uuid
from dotenv import load_dotenv


# ============================================================
# CONFIGURACION
# ============================================================

SYMBOL = "SPXW"

# strike_range=10 devuelve aproximadamente 20 strikes
# CALL + PUT = aproximadamente 40 contratos
STRIKE_RANGE = 10
OI_STRIKE_RANGE = 25

# Segundos entre actualizaciones
REFRESH_SECONDS = 5

# Control de calidad temporal para trades
TRADE_MAX_AGE_SECONDS = 15
TRADE_FUTURE_TOLERANCE_SECONDS = 2

# Archivo CSV donde se guardaran los snapshots
HISTORY_FOLDER = "historico_spx_0dte"
SIGNAL_HISTORY_FOLDER = "historico_senales_spx_0dte"
LIVE_OUTPUT_JSON = "spx_0dte_live.json"
STATE_FILE = "spx_0dte_state.json"

# Zona horaria del mercado
# Zona horaria del mercado
MARKET_TZ = ZoneInfo("America/New_York")

SAVE_START_HOUR = 9
SAVE_START_MINUTE = 30

SAVE_END_HOUR = 11
SAVE_END_MINUTE = 30

FORCED_EXIT_HOUR = 15
FORCED_EXIT_MINUTE = 30
SIGNAL_HISTORY_END_HOUR = 15
SIGNAL_HISTORY_END_MINUTE = 45

WALL_PROXIMITY_POINTS = 5.0
MIN_ABS_HEDGE_NOTIONAL = 10_000_000.0

EXPIRATION_HOUR = 16
EXPIRATION_MINUTE = 0

RISK_FREE_RATE = 0.04

ES_POINT_VALUE_USD = 50.0

DEFAULT_POSITION_SIZE_CONTRACTS = 1
DEFAULT_STOP_LOSS_POINTS = 15.0
DEFAULT_TAKE_PROFIT_POINTS = 30.0
DEFAULT_MAX_LOSS_USD = 750.0
EXECUTION_MODE = "DRY_RUN"
LIVE_ORDER_EXECUTION_ENABLED = False
ORDER_EXECUTION_ENVIRONMENT = "SIM"
CURRENT_EXECUTION_STATUS = "IDLE"
CURRENT_EXECUTION_ACTION = "NONE"
CURRENT_EXECUTION_REASON = "NO EXECUTION REQUEST"
TRADESTATION_ES_CONTRACT_SYMBOL = "ESZ26"
CURRENT_EXECUTION_SYMBOL = TRADESTATION_ES_CONTRACT_SYMBOL
CURRENT_EXECUTION_SIDE = "NONE"
CURRENT_EXECUTION_QUANTITY = 0
CURRENT_EXECUTION_ORDER_TYPE = "MARKET"

CURRENT_EXECUTION_SAFETY_OK = False
CURRENT_EXECUTION_SAFETY_REASON = "SAFETY CHECK NOT EVALUATED"

CURRENT_DISPATCH_STATUS = "IDLE"
CURRENT_DISPATCH_REASON = "NO DISPATCH"
CURRENT_DISPATCH_ID = None
CURRENT_BROKER_ORDER_ID = None
CURRENT_BROKER_ORDER_STATUS = "NONE"
CURRENT_BROKER_ORDER_STATUS_DESCRIPTION = "NONE"
CURRENT_BROKER_ORDER_STATE = "NONE"
LAST_DISPATCH_SIGNATURE = None
CURRENT_PENDING_ORDER_ACTION = "NONE"
CURRENT_PENDING_ORDER_SIDE = "NONE"
CURRENT_PENDING_ORDER_QUANTITY = 0
CURRENT_PENDING_ORDER_SYMBOL = None
CURRENT_PENDING_ORDER_SUBMITTED_AT = None
CURRENT_POSITION_STATE = "FLAT"
CURRENT_POSITION_VALID = True
CURRENT_POSITION_VALIDATION_REASON = "POSITION STATE VALID"
CURRENT_POSITION_CONTRACTS = 0
CURRENT_POSITION_ENTRY_SIDE = "NONE"
CURRENT_BROKER_ACCOUNT_ID = None
CURRENT_BROKER_POSITION_AVAILABLE = False
CURRENT_BROKER_POSITION_REASON = "BROKER POSITION NOT CHECKED"

CURRENT_POSITION_RECONCILIATION_OK = False
CURRENT_POSITION_RECONCILIATION_ACTION = "NONE"
CURRENT_POSITION_RECONCILIATION_REASON = "RECONCILIATION NOT CHECKED"

LAST_SEEN_TRADE = {}

OPEN_INTEREST_CACHE = None

DEALER_FLOW_POSITION = {}

LAST_DYNAMIC_CALL_WALL = None
LAST_DYNAMIC_PUT_WALL = None

CALL_WALL_STREAK = 0
PUT_WALL_STREAK = 0

CONFIRMED_CALL_WALL = None
CONFIRMED_PUT_WALL = None

CONFIRMED_CALL_WALL_MISSES = 0
CONFIRMED_PUT_WALL_MISSES = 0

CURRENT_GAMMA_BALANCE = 0.0
CURRENT_GAMMA_REGIME = "NEUTRAL / MIXED"

CURRENT_NET_DYNAMIC_GEX = 0.0
CURRENT_POSITIVE_DYNAMIC_GEX = 0.0
CURRENT_NEGATIVE_DYNAMIC_GEX = 0.0

CURRENT_DEALER_FLOW_GEX = 0.0
CURRENT_DEALER_DYNAMIC_GEX = 0.0

CURRENT_DEALER_DELTA_NOTIONAL = 0.0
CURRENT_DEALER_HEDGE_NOTIONAL = 0.0
CURRENT_ABS_HEDGE_NOTIONAL = 0.0
CURRENT_HEDGE_PRESSURE_BALANCE = 0.0
CURRENT_HEDGE_PRESSURE = "BLOCKED"

CURRENT_DIRECTIONAL_BIAS = "BLOCKED"
CURRENT_COMBINED_MARKET_STATE = "BLOCKED"

CURRENT_CALL_WALL_DISTANCE = None
CURRENT_PUT_WALL_DISTANCE = None
CURRENT_WALL_LOCATION = "UNAVAILABLE"
CURRENT_WALL_CONTEXT = "UNAVAILABLE"
CURRENT_FULL_MARKET_CONTEXT = "BLOCKED"

CURRENT_SIGNAL_CANDIDATE = "NONE"
CURRENT_SIGNAL_REASON = "INITIALIZING"
CURRENT_SETUP_QUALITY = "NONE"

SIGNAL_CONFIRMATION_CYCLES = 3
LAST_ACTIONABLE_SIGNAL_CANDIDATE = "NONE"
CURRENT_SIGNAL_CANDIDATE_STREAK = 0

CURRENT_CONFIRMED_SIGNAL = "NONE"
CURRENT_SIGNAL_CONFIRMED = False

CURRENT_RISK_STATUS = "BLOCKED"
CURRENT_RISK_PERMISSION = False
CURRENT_RISK_REASON = "RISK PARAMETERS NOT VALIDATED"
CURRENT_ENTRY_EXECUTION_PERMISSION = False
CURRENT_EXIT_EXECUTION_PERMISSION = False

CURRENT_POSITION_SIZE_CONTRACTS = DEFAULT_POSITION_SIZE_CONTRACTS
CURRENT_STOP_LOSS_POINTS = DEFAULT_STOP_LOSS_POINTS
CURRENT_TAKE_PROFIT_POINTS = DEFAULT_TAKE_PROFIT_POINTS
CURRENT_MAX_LOSS_USD = DEFAULT_MAX_LOSS_USD

CURRENT_FRESH_TRADES = 0
CURRENT_NEW_TRADES = 0
CURRENT_REJECTED_TRADES = 0

CURRENT_NEW_TRADE_AGE_MIN_SEC = None
CURRENT_NEW_TRADE_AGE_MAX_SEC = None

CURRENT_TEMPORAL_ACCEPTANCE_RATIO = 0.0
CURRENT_TEMPORAL_QUALITY = "NO NEW TRADES"

CURRENT_FLOW_DATA_STATUS = "BLOCKED"
CURRENT_FLOW_USABLE = False

CURRENT_FORCED_EXIT_REQUIRED = False
CURRENT_TRADING_STATUS = "ACTIVE"

CURRENT_OPERATIONAL_MODE = "BLOCKED"
CURRENT_SIGNAL_PERMISSION = False
CURRENT_OPERATIONAL_REASON = "INITIALIZING"

CURRENT_DEALER_SELL_OPTIONS = 0
CURRENT_DEALER_BUY_OPTIONS = 0

CURRENT_NEUTRAL_TRADES = 0
CURRENT_CLASSIFIED_TRADE_RATIO = 0.0
CURRENT_NEUTRAL_TRADE_RATIO = 0.0

LAST_FRESH_TRADE_CYCLE_TIME = None
CURRENT_FRESH_TRADE_AGE_SEC = 0.0
CURRENT_FLOW_FRESHNESS = "NO DATA"

def mark_new_trade(row):

    key = (
        row["symbol"],
        row["expiration"],
        row["strike"],
        row["right"]
    )

    trade_time = row["trade_time"]

    if pd.isna(trade_time):
        return False

    previous_trade_time = LAST_SEEN_TRADE.get(
        key
    )

    if previous_trade_time is None:
        LAST_SEEN_TRADE[key] = trade_time
        return False

    if previous_trade_time == trade_time:
        return False

    LAST_SEEN_TRADE[key] = trade_time

    return True

# ============================================================
# TRADESTATION
# ============================================================

load_dotenv("tradestation_tokens.env")

TS_ACCESS_TOKEN = os.getenv("TS_ACCESS_TOKEN")

TS_SPX_SYMBOL = "$SPX.X"

TS_QUOTE_URL = (
    "https://api.tradestation.com/"
    "v3/marketdata/quotes/"
    f"{TS_SPX_SYMBOL}"
)

TS_API_BASE_URL = "https://api.tradestation.com/v3"
TS_SIM_API_BASE_URL = "https://sim-api.tradestation.com/v3"

def get_tradestation_api_base_url():

    if ORDER_EXECUTION_ENVIRONMENT == "LIVE":
        return TS_API_BASE_URL

    if ORDER_EXECUTION_ENVIRONMENT == "SIM":
        return TS_SIM_API_BASE_URL

    raise ValueError(
        "INVALID ORDER EXECUTION ENVIRONMENT"
    )

def build_tradestation_order_payload():

    if CURRENT_EXECUTION_ACTION == "ENTRY":
        trade_action = (
            "BUY"
            if CURRENT_EXECUTION_SIDE == "BUY"
            else "SELL"
        )

        return {
            "AccountID": CURRENT_BROKER_ACCOUNT_ID,
            "Symbol": CURRENT_EXECUTION_SYMBOL,
            "Quantity": str(CURRENT_EXECUTION_QUANTITY),
            "OrderType": CURRENT_EXECUTION_ORDER_TYPE,
            "TradeAction": trade_action,
            "TimeInForce": {
                "Duration": "DAY"
            },
            "Route": "Intelligent"
        }

    if CURRENT_EXECUTION_ACTION == "EXIT":
        return {
            "AccountID": CURRENT_BROKER_ACCOUNT_ID,
            "Symbol": CURRENT_EXECUTION_SYMBOL,
            "Quantity": str(CURRENT_POSITION_CONTRACTS),
            "OrderType": CURRENT_EXECUTION_ORDER_TYPE,
            "TradeAction": (
                "SELL"
                if CURRENT_POSITION_STATE == "LONG"
                else "BUY"
            ),
            "TimeInForce": {
                "Duration": "DAY"
            },
            "Route": "Intelligent"
        }

    return None

def validate_tradestation_order_payload(payload):

    if payload is None:
        return False, "ORDER PAYLOAD IS NONE"

    required_fields = (
        "AccountID",
        "Symbol",
        "Quantity",
        "OrderType",
        "TradeAction",
        "TimeInForce",
        "Route",
    )

    for field in required_fields:
        if field not in payload:
            return False, f"MISSING ORDER FIELD: {field}"

    if not payload["Symbol"]:
        return False, "INVALID ORDER SYMBOL"

    try:
        quantity = int(payload["Quantity"])
    except (TypeError, ValueError):
        return False, "INVALID ORDER QUANTITY"

    if quantity <= 0:
        return False, "INVALID ORDER QUANTITY"

    if payload["OrderType"] != "MARKET":
        return False, "UNSUPPORTED ORDER TYPE"

    if payload["TradeAction"] not in (
        "BUY",
        "SELL",
    ):
        return False, "INVALID TRADE ACTION"

    if not isinstance(payload["TimeInForce"], dict):
        return False, "INVALID TIME IN FORCE"

    if payload["TimeInForce"].get("Duration") != "DAY":
        return False, "UNSUPPORTED TIME IN FORCE"

    if payload["Route"] != "Intelligent":
        return False, "UNSUPPORTED ROUTE"

    if payload["AccountID"] is None:
        return False, "ACCOUNT ID NOT AVAILABLE"

    return True, "ORDER PAYLOAD VALID"

# ============================================================
# CREAR CLIENTE THETADATA
# ============================================================

def refresh_tradestation_token():

    load_dotenv(
        "tradestation.env",
        override=True
    )

    load_dotenv(
        "tradestation_tokens.env",
        override=True
    )

    client_id = os.getenv(
        "TS_CLIENT_ID"
    )

    client_secret = os.getenv(
        "TS_CLIENT_SECRET"
    )

    refresh_token = os.getenv(
        "TS_REFRESH_TOKEN"
    )

    token_url = (
        "https://signin.tradestation.com/"
        "oauth/token"
    )

    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }

    response = requests.post(
        token_url,
        data=data,
        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"Error renovando token "
            f"TradeStation "
            f"{response.status_code}: "
            f"{response.text}"
        )

    tokens = response.json()

    access_token = tokens.get(
        "access_token"
    )

    new_refresh_token = tokens.get(
        "refresh_token",
        refresh_token
    )

    with open(
        "tradestation_tokens.env",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            f"TS_ACCESS_TOKEN="
            f"{access_token}\n"
        )

        f.write(
            f"TS_REFRESH_TOKEN="
            f"{new_refresh_token}\n"
        )

    return access_token

def get_tradestation_auth_headers():

    load_dotenv(
        "tradestation_tokens.env",
        override=True
    )

    access_token = os.getenv(
        "TS_ACCESS_TOKEN"
    )

    if not access_token:
        raise RuntimeError(
            "TS_ACCESS_TOKEN NOT AVAILABLE"
        )

    return {
        "Authorization": (
            f"Bearer {access_token}"
        ),
        "Content-Type": "application/json",
    }

def tradestation_request(
    method,
    url,
    *,
    json_payload=None,
    timeout=30
):

    headers = get_tradestation_auth_headers()

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=json_payload,
        timeout=timeout
    )

    if response.status_code == 401:

        access_token = (
            refresh_tradestation_token()
        )

        headers["Authorization"] = (
            f"Bearer {access_token}"
        )

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_payload,
            timeout=timeout
        )

    return response

def get_tradestation_accounts():

    base_url = get_tradestation_api_base_url()

    url = (
        f"{base_url}/"
        "brokerage/accounts"
    )

    try:
        response = tradestation_request(
            "GET",
            url,
            timeout=10
        )

    except requests.exceptions.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "reason": (
                "POSITION REQUEST FAILED: "
                f"{type(exc).__name__}"
            ),
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

def get_primary_tradestation_account_id():

    result = get_tradestation_accounts()

    if not result.get("ok"):
        return None, result.get(
            "reason",
            "ACCOUNT LOOKUP FAILED"
        )

    accounts = result.get(
        "accounts",
        []
    )

    if not accounts:
        return None, "NO TRADESTATION ACCOUNTS"

    for account in accounts:

        if (
            account.get("AccountType") == "Futures"
            and account.get("Status") == "Active"
        ):

            account_id = account.get(
                "AccountID"
            )

            if account_id:
                return (
                    account_id,
                    "ACTIVE FUTURES ACCOUNT AVAILABLE"
                )

    return None, "NO ACTIVE FUTURES ACCOUNT"

def get_tradestation_positions(account_id):

    if not account_id:
        return {
            "ok": False,
            "status_code": None,
            "reason": "ACCOUNT ID NOT AVAILABLE",
            "positions": [],
        }

    base_url = get_tradestation_api_base_url()

    url = (
        f"{base_url}/"
        f"brokerage/accounts/{account_id}/positions"
    )

    try:
        response = tradestation_request(
            "GET",
            url,
            timeout=10
        )

    except requests.exceptions.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "reason": (
                "POSITION REQUEST FAILED: "
                f"{type(exc).__name__}"
            ),
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

def get_tradestation_es_position(account_id):

    result = get_tradestation_positions(
        account_id
    )

    if not result.get("ok"):
        return {
            "ok": False,
            "reason": result.get(
                "reason",
                "POSITION LOOKUP FAILED"
            ),
            "position": None,
        }

    positions = result.get(
        "positions",
        []
    )

    for position in positions:

        symbol = str(
            position.get(
                "Symbol",
                ""
            )
        ).upper()

        if symbol == CURRENT_EXECUTION_SYMBOL.upper():
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

def classify_tradestation_order_status(
    status,
    status_description
):

    status_text = str(
        status or ""
    ).strip().upper()

    description_text = str(
        status_description or ""
    ).strip().upper()

    if description_text in (
        "FILLED",
        "FULLY FILLED",
    ):
        return "FILLED"

    if description_text in (
        "CANCELLED",
        "CANCELED",
    ):
        return "CANCELLED"

    if description_text == "REJECTED":
        return "REJECTED"

    if description_text in (
        "SENT",
        "RECEIVED",
        "OPEN",
    ):
        return "OPEN"

    if status_text in (
        "ACK",
        "OPN",
    ):
        return "OPEN"

    return "UNKNOWN"

def get_tradestation_order_by_id(
    account_id,
    order_id
):

    if not account_id:
        return {
            "ok": False,
            "status_code": None,
            "reason": "ACCOUNT ID MISSING",
            "order": None,
        }

    if not order_id:
        return {
            "ok": False,
            "status_code": None,
            "reason": "ORDER ID MISSING",
            "order": None,
        }

    base_url = get_tradestation_api_base_url()

    url = (
        f"{base_url}/brokerage/accounts/"
        f"{account_id}/orders/{order_id}"
    )

    try:
        response = tradestation_request(
            "GET",
            url,
            timeout=10
        )

    except requests.exceptions.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "reason": (
                "ORDER STATUS REQUEST FAILED: "
                f"{type(exc).__name__}"
            ),
            "order": None,
        }

    if response.status_code != 200:
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": response.text,
            "order": None,
        }

    try:
        data = response.json()

    except ValueError:
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": "ORDER STATUS RESPONSE INVALID JSON",
            "order": None,
        }

    orders = data.get(
        "Orders",
        []
    )

    if not isinstance(orders, list):
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": "ORDER STATUS RESPONSE INVALID ORDERS",
            "order": None,
        }

    for order in orders:

        if str(
            order.get(
                "OrderID",
                ""
            )
        ) == str(order_id):

            return {
                "ok": True,
                "status_code": response.status_code,
                "reason": "ORDER RETRIEVED",
                "order": order,
            }

    return {
        "ok": False,
        "status_code": response.status_code,
        "reason": "ORDER NOT FOUND",
        "order": None,
    }

def get_tradestation_orders(account_id):

    if not account_id:
        return {
            "ok": False,
            "status_code": None,
            "reason": "ACCOUNT ID MISSING",
            "orders": [],
        }

    base_url = get_tradestation_api_base_url()

    url = (
        f"{base_url}/brokerage/accounts/"
        f"{account_id}/orders"
    )

    try:
        response = tradestation_request(
            "GET",
            url,
            timeout=10
        )

    except requests.exceptions.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "reason": (
                "ORDERS REQUEST FAILED: "
                f"{type(exc).__name__}"
            ),
            "orders": [],
        }

    if response.status_code != 200:
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": response.text,
            "orders": [],
        }

    try:
        data = response.json()

    except ValueError:
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": "ORDERS RESPONSE INVALID JSON",
            "orders": [],
        }

    orders = data.get(
        "Orders",
        []
    )

    if not isinstance(orders, list):
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": "ORDERS RESPONSE INVALID ORDERS",
            "orders": [],
        }

    return {
        "ok": True,
        "status_code": response.status_code,
        "reason": "ORDERS RETRIEVED",
        "orders": orders,
    }

def get_tradestation_historical_orders(account_id, since):

    if not account_id:
        return {
            "ok": False,
            "status_code": None,
            "reason": "ACCOUNT ID MISSING",
            "orders": [],
        }

    if not since:
        return {
            "ok": False,
            "status_code": None,
            "reason": "SINCE DATE MISSING",
            "orders": [],
        }

    base_url = get_tradestation_api_base_url()

    url = (
        f"{base_url}/brokerage/accounts/"
        f"{account_id}/historicalorders"
        f"?since={since}"
    )

    try:
        response = tradestation_request(
            "GET",
            url,
            timeout=10
        )

    except requests.exceptions.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "reason": (
                "HISTORICAL ORDERS REQUEST FAILED: "
                f"{type(exc).__name__}"
            ),
            "orders": [],
        }

    if response.status_code != 200:
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": response.text,
            "orders": [],
        }

    try:
        data = response.json()

    except ValueError:
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": "HISTORICAL ORDERS RESPONSE INVALID JSON",
            "orders": [],
        }

    orders = data.get(
        "Orders",
        []
    )

    if not isinstance(orders, list):
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": "HISTORICAL ORDERS RESPONSE INVALID ORDERS",
            "orders": [],
        }

    return {
        "ok": True,
        "status_code": response.status_code,
        "reason": "HISTORICAL ORDERS RETRIEVED",
        "orders": orders,
    }

def match_pending_order(order, pending):

    if not isinstance(order, dict):
        return False

    order_id = order.get("OrderID")

    if (
        order_id is None
        or not isinstance(order_id, (str, int))
        or not str(order_id).strip()
    ):
        return False    

    if not isinstance(pending, dict):
        return False

    legs = order.get("Legs", [])

    if not isinstance(legs, list) or len(legs) != 1:
        return False

    leg = legs[0]

    if not isinstance(leg, dict):
        return False

    symbol = leg.get("Symbol", order.get("Symbol"))

    trade_action = leg.get(
        "BuyOrSell",
        leg.get("TradeAction")
    )

    quantity = order.get(
        "Quantity",
        leg.get("QuantityOrdered")
    )

    try:
        quantity_matches = (
            float(quantity) == float(pending["quantity"])
        )
    except (TypeError, ValueError, KeyError):
        return False

    opened_at = order.get("OpenedDateTime")
    submitted_at = pending.get("submitted_at")

    if not opened_at or not submitted_at:
        return False

    try:
        order_time = datetime.fromisoformat(
            str(opened_at).replace("Z", "+00:00")
        )

        pending_time = datetime.fromisoformat(
            str(submitted_at).replace("Z", "+00:00")
        )

        if (
            order_time.utcoffset() is None
            or pending_time.utcoffset() is None
        ):
            return False

        time_difference = (
            order_time - pending_time
        ).total_seconds()

    except (TypeError, ValueError, OverflowError):
        return False

    if not -30 <= time_difference <= 300:
        return False

    return (
        str(symbol or "").upper()
        == str(pending.get("symbol") or "").upper()
        and str(trade_action or "").upper()
        == str(pending.get("side") or "").upper()
        and quantity_matches
    )

def find_matching_pending_orders(orders, pending):

    if not isinstance(orders, list):
        return {
            "status": "INVALID_ORDERS",
            "matches": [],
            "match_count": 0,
        }

    if not isinstance(pending, dict):
        return {
            "status": "INVALID_PENDING",
            "matches": [],
            "match_count": 0,
        }

    matches = []
    seen_orders = {}
    conflicting_orders = []
    invalid_execution_orders = []
    partial_execution_orders = []

    for order in orders:

        if not match_pending_order(order, pending):
            continue

        leg = order["Legs"][0]

        exec_quantity_raw = order.get("ExecQuantity")

        if exec_quantity_raw is None:
            exec_quantity_raw = leg.get("ExecQuantity")

        ordered_quantity_raw = order.get("Quantity")

        if ordered_quantity_raw is None:
            ordered_quantity_raw = leg.get("QuantityOrdered")

        if exec_quantity_raw is not None:
            try:
                ordered_quantity = float(ordered_quantity_raw)
                executed_quantity = float(exec_quantity_raw)

                valid_execution_quantity = (
                    math.isfinite(executed_quantity)
                    and math.isfinite(ordered_quantity)
                    and ordered_quantity > 0
                    and 0 <= executed_quantity <= ordered_quantity
                    and executed_quantity.is_integer()
                )

            except (TypeError, ValueError, OverflowError, KeyError):
                valid_execution_quantity = False

            if not valid_execution_quantity:
                invalid_execution_orders.append(order)

            elif 0 < executed_quantity < ordered_quantity:
                partial_execution_orders.append(order)

        order_id = str(order["OrderID"]).strip()

        if order_id in seen_orders:

            previous = seen_orders[order_id]

            previous_status = previous.get("Status")
            current_status = order.get("Status")

            previous_description = previous.get(
                "StatusDescription"
            )
            current_description = order.get(
                "StatusDescription"
            )

            status_conflict = (
                previous_status is not None
                and current_status is not None
                and previous_status != current_status
            )

            description_conflict = (
                previous_description is not None
                and current_description is not None
                and previous_description != current_description
            )

            previous_exec_quantity = previous.get("ExecQuantity")
            current_exec_quantity = order.get("ExecQuantity")

            previous_legs = previous.get("Legs", [])
            current_legs = order.get("Legs", [])

            if (
                previous_exec_quantity is None
                and isinstance(previous_legs, list)
                and len(previous_legs) == 1
                and isinstance(previous_legs[0], dict)
            ):
                previous_exec_quantity = previous_legs[0].get(
                    "ExecQuantity"
                )

            if (
                current_exec_quantity is None
                and isinstance(current_legs, list)
                and len(current_legs) == 1
                and isinstance(current_legs[0], dict)
            ):
                current_exec_quantity = current_legs[0].get(
                    "ExecQuantity"
                )

            if (
                (previous_exec_quantity is None)
                != (current_exec_quantity is None)
            ):
                execution_quantity_changed = True

            elif (
                previous_exec_quantity is None
                and current_exec_quantity is None
            ):
                execution_quantity_changed = False

            else:
                try:
                    execution_quantity_changed = (
                        float(previous_exec_quantity)
                        != float(current_exec_quantity)
                    )

                except (TypeError, ValueError, OverflowError):
                    execution_quantity_changed = True

            if (
                status_conflict
                or description_conflict
                or execution_quantity_changed
            ):
                conflicting_orders.append({
                    "OrderID": order_id,
                    "first_record": previous,
                    "second_record": order,
                })

            continue

        seen_orders[order_id] = order
        matches.append(order)

    invalid_execution_orders = list({
        str(order["OrderID"]).strip(): order
        for order in invalid_execution_orders
    }.values())

    partial_execution_orders = list({
        str(order["OrderID"]).strip(): order
        for order in partial_execution_orders
    }.values())
    
    if invalid_execution_orders:
        status = "INVALID_EXEC_QUANTITY"

    elif conflicting_orders:
        status = "STATUS_CONFLICT"

    elif partial_execution_orders:
        status = "PARTIAL_EXECUTION"

    elif len(matches) == 0:
        status = "NO_MATCH"

    elif len(matches) == 1:
        status = "SINGLE_MATCH"

    else:
        status = "AMBIGUOUS"

    return {
        "status": status,
        "matches": matches,
        "match_count": len(matches),
        "conflicting_orders": conflicting_orders,
        "invalid_execution_orders": invalid_execution_orders,
        "partial_execution_orders": partial_execution_orders,
    }    

def reconcile_pending_order(account_id, pending):

    if not account_id:
        return {
            "ok": False,
            "status": "INVALID_ACCOUNT",
            "reason": "ACCOUNT ID MISSING",
        }

    if not isinstance(pending, dict):
        return {
            "ok": False,
            "status": "INVALID_PENDING",
            "reason": "PENDING ORDER INVALID",
        }

    submitted_at = pending.get("submitted_at")

    if not submitted_at:
        return {
            "ok": False,
            "status": "INVALID_PENDING_TIME",
            "reason": "PENDING SUBMITTED TIME MISSING",
        }

    try:
        submitted_time = datetime.fromisoformat(
            str(submitted_at).replace("Z", "+00:00")
        )

        if submitted_time.utcoffset() is None:
            raise ValueError("NAIVE DATETIME")

    except (TypeError, ValueError, OverflowError):
        return {
            "ok": False,
            "status": "INVALID_PENDING_TIME",
            "reason": "PENDING SUBMITTED TIME INVALID",
        }

    submitted_date = submitted_time.date()
    today_market = datetime.now(MARKET_TZ).date()

    if submitted_date >= today_market:
        since = (today_market - timedelta(days=1)).isoformat()
    else:
        since = submitted_date.isoformat()

    current_result = get_tradestation_orders(account_id)

    if not current_result.get("ok"):
        return {
            "ok": False,
            "status": "CURRENT_ORDERS_QUERY_FAILED",
            "reason": current_result.get("reason"),
        }

    historical_result = get_tradestation_historical_orders(
        account_id,
        since
    )

    if not historical_result.get("ok"):
        return {
            "ok": False,
            "status": "HISTORICAL_ORDERS_QUERY_FAILED",
            "reason": historical_result.get("reason"),
        }

    combined_orders = (
        current_result.get("orders", [])
        + historical_result.get("orders", [])
    )

    match_result = find_matching_pending_orders(
        combined_orders,
        pending
    )

    return {
        "ok": True,
        "status": match_result["status"],
        "reason": "PENDING ORDER RECONCILIATION COMPLETE",
        "matches": match_result["matches"],
        "match_count": match_result["match_count"],
        "conflicting_orders": match_result.get(
            "conflicting_orders",
            []
        ),
        "invalid_execution_orders": match_result.get(
            "invalid_execution_orders",
            []
        ),
        "partial_execution_orders": match_result.get(
            "partial_execution_orders",
            []
        ),
        "current_orders_count": len(
            current_result.get("orders", [])
        ),
        "historical_orders_count": len(
            historical_result.get("orders", [])
        ),
        "since": since,
    }

def submit_tradestation_order(payload):

    if not LIVE_ORDER_EXECUTION_ENABLED:
        return {
            "ok": False,
            "status_code": None,
            "reason": "LIVE ORDER EXECUTION DISABLED",
            "response": None,
        }

    if ORDER_EXECUTION_ENVIRONMENT != "SIM":
        return {
            "ok": False,
            "status_code": None,
            "reason": "ORDER EXECUTION ENVIRONMENT NOT SIM",
            "response": None,
        }

    valid, reason = (
        validate_tradestation_order_payload(
            payload
        )
    )

    if not valid:
        return {
            "ok": False,
            "status_code": None,
            "reason": reason,
            "response": None,
        }

    base_url = (
        get_tradestation_api_base_url()
    )

    url = (
        f"{base_url}/"
        "orderexecution/orders"
    )

    try:
        response = tradestation_request(
            "POST",
            url,
            json_payload=payload,
            timeout=30
        )

    except requests.exceptions.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "reason": (
                "ORDER SUBMISSION STATUS UNKNOWN: "
                f"{type(exc).__name__}"
            ),
            "response": None,
        }

    if response.status_code not in (
        200,
        201,
    ):
        return {
            "ok": False,
            "status_code": response.status_code,
            "reason": response.text,
            "response": None,
        }

    try:
        response_data = response.json()

    except ValueError:
        response_data = {
            "raw_text": response.text
        }

    return {
        "ok": True,
        "status_code": response.status_code,
        "reason": "ORDER SUBMITTED",
        "response": response_data,
    }

def normalize_tradestation_es_position(position):

    if not position:
        return {
            "state": "FLAT",
            "contracts": 0,
            "entry_side": "NONE",
        }

    quantity = position.get(
        "Quantity",
        0
    )

    try:
        quantity = int(
            float(quantity)
        )
    except (TypeError, ValueError):
        return {
            "state": "UNKNOWN",
            "contracts": 0,
            "entry_side": "NONE",
        }

    if quantity > 0:
        return {
            "state": "LONG",
            "contracts": quantity,
            "entry_side": "BUY",
        }

    if quantity < 0:
        return {
            "state": "SHORT",
            "contracts": abs(quantity),
            "entry_side": "SELL",
        }

    return {
        "state": "FLAT",
        "contracts": 0,
        "entry_side": "NONE",
    }

def compare_internal_vs_broker_position(
    broker_position
):

    normalized = (
        normalize_tradestation_es_position(
            broker_position
        )
    )

    broker_state = normalized["state"]
    broker_contracts = normalized["contracts"]
    broker_entry_side = normalized["entry_side"]

    if broker_state == "UNKNOWN":
        return {
            "match": False,
            "reason": "BROKER POSITION UNKNOWN",
            "broker_state": broker_state,
            "broker_contracts": broker_contracts,
            "broker_entry_side": broker_entry_side,
        }

    if (
        CURRENT_POSITION_STATE == broker_state
        and CURRENT_POSITION_CONTRACTS == broker_contracts
        and CURRENT_POSITION_ENTRY_SIDE == broker_entry_side
    ):
        return {
            "match": True,
            "reason": "INTERNAL AND BROKER POSITION MATCH",
            "broker_state": broker_state,
            "broker_contracts": broker_contracts,
            "broker_entry_side": broker_entry_side,
        }

    return {
        "match": False,
        "reason": "INTERNAL AND BROKER POSITION MISMATCH",
        "broker_state": broker_state,
        "broker_contracts": broker_contracts,
        "broker_entry_side": broker_entry_side,
    }

def reconcile_internal_with_broker_position(
    broker_position
):

    comparison = (
        compare_internal_vs_broker_position(
            broker_position
        )
    )

    if comparison["match"]:
        return {
            "ok": True,
            "action": "NONE",
            "reason": comparison["reason"],
        }

    if comparison["broker_state"] == "UNKNOWN":
        return {
            "ok": False,
            "action": "BLOCK",
            "reason": "BROKER POSITION UNKNOWN",
        }

    return {
        "ok": False,
        "action": "BLOCK",
        "reason": (
            "POSITION RECONCILIATION REQUIRED"
        ),
    }

def update_broker_reconciliation_state(
    account_id,
    broker_lookup_result
):

    global CURRENT_BROKER_ACCOUNT_ID
    global CURRENT_BROKER_POSITION_AVAILABLE
    global CURRENT_BROKER_POSITION_REASON
    global CURRENT_POSITION_RECONCILIATION_OK
    global CURRENT_POSITION_RECONCILIATION_ACTION
    global CURRENT_POSITION_RECONCILIATION_REASON

    CURRENT_BROKER_ACCOUNT_ID = account_id

    if not broker_lookup_result.get("ok"):
        CURRENT_BROKER_POSITION_AVAILABLE = False
        CURRENT_BROKER_POSITION_REASON = (
            broker_lookup_result.get(
                "reason",
                "BROKER POSITION LOOKUP FAILED"
            )
        )

        CURRENT_POSITION_RECONCILIATION_OK = False
        CURRENT_POSITION_RECONCILIATION_ACTION = "BLOCK"
        CURRENT_POSITION_RECONCILIATION_REASON = (
            "BROKER POSITION UNAVAILABLE"
        )

        return

    CURRENT_BROKER_POSITION_AVAILABLE = True
    CURRENT_BROKER_POSITION_REASON = (
        broker_lookup_result.get(
            "reason",
            "BROKER POSITION AVAILABLE"
        )
    )

    reconciliation = (
        reconcile_internal_with_broker_position(
            broker_lookup_result.get(
                "position"
            )
        )
    )

    CURRENT_POSITION_RECONCILIATION_OK = (
        reconciliation.get(
            "ok",
            False
        )
    )

    CURRENT_POSITION_RECONCILIATION_ACTION = (
        reconciliation.get(
            "action",
            "BLOCK"
        )
    )

    CURRENT_POSITION_RECONCILIATION_REASON = (
        reconciliation.get(
            "reason",
            "RECONCILIATION FAILED"
        )
    )

def refresh_broker_reconciliation():

    account_id, account_reason = (
        get_primary_tradestation_account_id()
    )

    if not account_id:
        update_broker_reconciliation_state(
            None,
            {
                "ok": False,
                "reason": account_reason,
                "position": None,
            }
        )

        return (
            CURRENT_POSITION_RECONCILIATION_OK,
            CURRENT_POSITION_RECONCILIATION_REASON,
        )

    broker_lookup_result = (
        get_tradestation_es_position(
            account_id
        )
    )

    update_broker_reconciliation_state(
        account_id,
        broker_lookup_result
    )

    return (
        CURRENT_POSITION_RECONCILIATION_OK,
        CURRENT_POSITION_RECONCILIATION_REASON,
    )    

def build_execution_intent():
    global CURRENT_EXECUTION_STATUS
    global CURRENT_EXECUTION_ACTION
    global CURRENT_EXECUTION_REASON
    global CURRENT_EXECUTION_SYMBOL
    global CURRENT_EXECUTION_SIDE
    global CURRENT_EXECUTION_QUANTITY
    global CURRENT_EXECUTION_ORDER_TYPE

    CURRENT_EXECUTION_STATUS = "IDLE"
    CURRENT_EXECUTION_ACTION = "NONE"
    CURRENT_EXECUTION_REASON = "NO EXECUTION REQUEST"
    CURRENT_EXECUTION_SYMBOL = TRADESTATION_ES_CONTRACT_SYMBOL
    CURRENT_EXECUTION_SIDE = "NONE"
    CURRENT_EXECUTION_QUANTITY = 0
    CURRENT_EXECUTION_ORDER_TYPE = "MARKET"

    if CURRENT_ENTRY_EXECUTION_PERMISSION:

        if CURRENT_CONFIRMED_SIGNAL in (
            "LONG MEAN REVERSION",
            "LONG BREAKOUT",
        ):
            CURRENT_EXECUTION_STATUS = "READY"
            CURRENT_EXECUTION_ACTION = "ENTRY"
            CURRENT_EXECUTION_REASON = CURRENT_CONFIRMED_SIGNAL
            CURRENT_EXECUTION_SIDE = "BUY"
            CURRENT_EXECUTION_QUANTITY = CURRENT_POSITION_SIZE_CONTRACTS

        elif CURRENT_CONFIRMED_SIGNAL in (
            "SHORT MEAN REVERSION",
            "SHORT BREAKDOWN",
        ):
            CURRENT_EXECUTION_STATUS = "READY"
            CURRENT_EXECUTION_ACTION = "ENTRY"
            CURRENT_EXECUTION_REASON = CURRENT_CONFIRMED_SIGNAL
            CURRENT_EXECUTION_SIDE = "SELL"
            CURRENT_EXECUTION_QUANTITY = CURRENT_POSITION_SIZE_CONTRACTS

    elif CURRENT_EXIT_EXECUTION_PERMISSION:
        CURRENT_EXECUTION_STATUS = "READY"
        CURRENT_EXECUTION_ACTION = "EXIT"
        CURRENT_EXECUTION_REASON = "FORCED EXIT"
        CURRENT_EXECUTION_SIDE = "FLATTEN"
        CURRENT_EXECUTION_QUANTITY = 0

def execution_safety_check():

    if EXECUTION_MODE != "LIVE":
        return False, "EXECUTION MODE IS NOT LIVE"

    if not LIVE_ORDER_EXECUTION_ENABLED:
        return False, "LIVE ORDER EXECUTION DISABLED"

    if not CURRENT_POSITION_RECONCILIATION_OK:
        return False, "POSITION RECONCILIATION NOT OK"

    if CURRENT_EXECUTION_STATUS != "READY":
        return False, "EXECUTION STATUS NOT READY"

    position_valid, position_reason = validate_position_state()

    if not position_valid:
        return False, position_reason

    if CURRENT_EXECUTION_ACTION not in ("ENTRY", "EXIT"):
        return False, "INVALID EXECUTION ACTION"

    if CURRENT_EXECUTION_ACTION == "ENTRY":

        if CURRENT_EXECUTION_SIDE not in ("BUY", "SELL"):
            return False, "INVALID ENTRY SIDE"

        if CURRENT_EXECUTION_QUANTITY <= 0:
            return False, "INVALID ENTRY QUANTITY"

    if CURRENT_EXECUTION_ACTION == "EXIT":

        if CURRENT_EXECUTION_SIDE != "FLATTEN":
            return False, "INVALID EXIT SIDE"

    return True, "EXECUTION SAFETY CHECK PASSED"

def dispatch_execution():
    global LAST_DISPATCH_SIGNATURE
    global CURRENT_POSITION_STATE
    global CURRENT_POSITION_CONTRACTS
    global CURRENT_POSITION_ENTRY_SIDE
    global CURRENT_BROKER_ORDER_STATE
    global CURRENT_PENDING_ORDER_ACTION
    global CURRENT_PENDING_ORDER_SIDE
    global CURRENT_PENDING_ORDER_QUANTITY
    global CURRENT_PENDING_ORDER_SYMBOL
    global CURRENT_PENDING_ORDER_SUBMITTED_AT

    safety_ok, safety_reason = execution_safety_check()

    if CURRENT_EXECUTION_STATUS != "READY":
        LAST_DISPATCH_SIGNATURE = None

        return {
            "status": "IDLE",
            "action": "NONE",
            "side": "NONE",
            "quantity": 0,
            "symbol": CURRENT_EXECUTION_SYMBOL,
            "order_type": CURRENT_EXECUTION_ORDER_TYPE,
            "reason": "NO EXECUTION REQUEST",
            "safety_ok": safety_ok,
            "safety_reason": safety_reason,
        }

    if CURRENT_BROKER_ORDER_STATE in (
        "OPEN",
        "UNKNOWN",
    ):
        return {
            "status": "ORDER_BLOCKED",
            "action": CURRENT_EXECUTION_ACTION,
            "side": CURRENT_EXECUTION_SIDE,
            "quantity": CURRENT_EXECUTION_QUANTITY,
            "symbol": CURRENT_EXECUTION_SYMBOL,
            "order_type": CURRENT_EXECUTION_ORDER_TYPE,
            "reason": (
                f"ORDER BLOCKED: BROKER ORDER STATE "
                f"{CURRENT_BROKER_ORDER_STATE}"
            ),
            "safety_ok": safety_ok,
            "safety_reason": safety_reason,
        }

    if (
        CURRENT_EXECUTION_ACTION == "ENTRY"
        and CURRENT_POSITION_STATE != "FLAT"
    ):
        return {
            "status": "POSITION_BLOCKED",
            "action": CURRENT_EXECUTION_ACTION,
            "side": CURRENT_EXECUTION_SIDE,
            "quantity": CURRENT_EXECUTION_QUANTITY,
            "symbol": CURRENT_EXECUTION_SYMBOL,
            "order_type": CURRENT_EXECUTION_ORDER_TYPE,
            "reason": (
                f"ENTRY BLOCKED: POSITION STATE "
                f"{CURRENT_POSITION_STATE}"
            ),
            "safety_ok": safety_ok,
            "safety_reason": safety_reason,
        }

    if (
        CURRENT_EXECUTION_ACTION == "EXIT"
        and CURRENT_POSITION_STATE == "FLAT"
    ):
        return {
            "status": "POSITION_BLOCKED",
            "action": CURRENT_EXECUTION_ACTION,
            "side": CURRENT_EXECUTION_SIDE,
            "quantity": CURRENT_EXECUTION_QUANTITY,
            "symbol": CURRENT_EXECUTION_SYMBOL,
            "order_type": CURRENT_EXECUTION_ORDER_TYPE,
            "reason": "EXIT BLOCKED: POSITION STATE FLAT",
            "safety_ok": safety_ok,
            "safety_reason": safety_reason,
        }

    dispatch_signature = (
        CURRENT_EXECUTION_ACTION,
        CURRENT_EXECUTION_SIDE,
        CURRENT_EXECUTION_QUANTITY,
        CURRENT_EXECUTION_REASON,
    )

    if dispatch_signature == LAST_DISPATCH_SIGNATURE:
        return {
            "status": "DUPLICATE_BLOCKED",
            "action": CURRENT_EXECUTION_ACTION,
            "side": CURRENT_EXECUTION_SIDE,
            "quantity": CURRENT_EXECUTION_QUANTITY,
            "symbol": CURRENT_EXECUTION_SYMBOL,
            "order_type": CURRENT_EXECUTION_ORDER_TYPE,
            "reason": "DUPLICATE EXECUTION INTENT",
            "safety_ok": safety_ok,
            "safety_reason": safety_reason,
        }

    if EXECUTION_MODE == "DRY_RUN":
        LAST_DISPATCH_SIGNATURE = dispatch_signature

        if CURRENT_EXECUTION_ACTION == "ENTRY":

            if CURRENT_EXECUTION_SIDE == "BUY":
                CURRENT_POSITION_STATE = "LONG"
                CURRENT_POSITION_ENTRY_SIDE = "BUY"

            elif CURRENT_EXECUTION_SIDE == "SELL":
                CURRENT_POSITION_STATE = "SHORT"
                CURRENT_POSITION_ENTRY_SIDE = "SELL"

            CURRENT_POSITION_CONTRACTS = (
                CURRENT_EXECUTION_QUANTITY
            )

        elif CURRENT_EXECUTION_ACTION == "EXIT":
            CURRENT_POSITION_STATE = "FLAT"
            CURRENT_POSITION_CONTRACTS = 0
            CURRENT_POSITION_ENTRY_SIDE = "NONE"    

        return {
            "status": "SIMULATED",
            "action": CURRENT_EXECUTION_ACTION,
            "side": CURRENT_EXECUTION_SIDE,
            "quantity": CURRENT_EXECUTION_QUANTITY,
            "symbol": CURRENT_EXECUTION_SYMBOL,
            "order_type": CURRENT_EXECUTION_ORDER_TYPE,
            "reason": "DRY RUN EXECUTION SIMULATED",
            "safety_ok": safety_ok,
            "safety_reason": safety_reason,
        }

    if not safety_ok:
        return {
            "status": "BLOCKED",
            "action": CURRENT_EXECUTION_ACTION,
            "side": CURRENT_EXECUTION_SIDE,
            "quantity": CURRENT_EXECUTION_QUANTITY,
            "symbol": CURRENT_EXECUTION_SYMBOL,
            "order_type": CURRENT_EXECUTION_ORDER_TYPE,
            "reason": safety_reason,
            "safety_ok": False,
            "safety_reason": safety_reason,
        }

    order_payload = build_tradestation_order_payload()

    payload_valid, payload_reason = (
        validate_tradestation_order_payload(
            order_payload
        )
    )

    if not payload_valid:
        return {
            "status": "PAYLOAD_BLOCKED",
            "action": CURRENT_EXECUTION_ACTION,
            "side": CURRENT_EXECUTION_SIDE,
            "quantity": CURRENT_EXECUTION_QUANTITY,
            "symbol": CURRENT_EXECUTION_SYMBOL,
            "order_type": CURRENT_EXECUTION_ORDER_TYPE,
            "reason": payload_reason,
            "safety_ok": True,
            "safety_reason": safety_reason,
        }

    LAST_DISPATCH_SIGNATURE = dispatch_signature
    CURRENT_PENDING_ORDER_ACTION = CURRENT_EXECUTION_ACTION
    CURRENT_PENDING_ORDER_SIDE = order_payload["TradeAction"]
    CURRENT_PENDING_ORDER_QUANTITY = int(order_payload["Quantity"])
    CURRENT_PENDING_ORDER_SYMBOL = CURRENT_EXECUTION_SYMBOL
    CURRENT_PENDING_ORDER_SUBMITTED_AT = datetime.now(
        MARKET_TZ
    ).isoformat()

    submit_result = submit_tradestation_order(
        order_payload
    )

    return {
        "status": (
            "SUBMITTED"
            if submit_result.get("ok")
            else "SUBMIT_FAILED"
        ),
        "action": CURRENT_EXECUTION_ACTION,
        "side": CURRENT_EXECUTION_SIDE,
        "quantity": CURRENT_EXECUTION_QUANTITY,
        "symbol": CURRENT_EXECUTION_SYMBOL,
        "order_type": CURRENT_EXECUTION_ORDER_TYPE,
        "reason": submit_result.get(
            "reason",
            "ORDER SUBMISSION RESULT UNKNOWN"
        ),
        "safety_ok": True,
        "safety_reason": safety_reason,
        "broker_response": submit_result.get("response"),
        "broker_status_code": submit_result.get("status_code"),
        "pending_order_action": CURRENT_PENDING_ORDER_ACTION,
        "pending_order_side": CURRENT_PENDING_ORDER_SIDE,
        "pending_order_quantity": CURRENT_PENDING_ORDER_QUANTITY,
        "pending_order_symbol": CURRENT_PENDING_ORDER_SYMBOL,
        "pending_order_submitted_at": CURRENT_PENDING_ORDER_SUBMITTED_AT,
    }

def validate_position_state():

    if CURRENT_POSITION_STATE == "FLAT":
        if CURRENT_POSITION_CONTRACTS != 0:
            return False, "FLAT POSITION WITH NONZERO CONTRACTS"

        if CURRENT_POSITION_ENTRY_SIDE != "NONE":
            return False, "FLAT POSITION WITH ENTRY SIDE"

    elif CURRENT_POSITION_STATE == "LONG":
        if CURRENT_POSITION_CONTRACTS <= 0:
            return False, "LONG POSITION WITH INVALID CONTRACTS"

        if CURRENT_POSITION_ENTRY_SIDE != "BUY":
            return False, "LONG POSITION WITH INVALID ENTRY SIDE"

    elif CURRENT_POSITION_STATE == "SHORT":
        if CURRENT_POSITION_CONTRACTS <= 0:
            return False, "SHORT POSITION WITH INVALID CONTRACTS"

        if CURRENT_POSITION_ENTRY_SIDE != "SELL":
            return False, "SHORT POSITION WITH INVALID ENTRY SIDE"

    else:
        return False, "UNKNOWN POSITION STATE"

    return True, "POSITION STATE VALID"      

def get_time_to_expiration(now_et):

    expiration_dt = now_et.replace(
        hour=EXPIRATION_HOUR,
        minute=EXPIRATION_MINUTE,
        second=0,
        microsecond=0
    )

    seconds_left = (
        expiration_dt - now_et
    ).total_seconds()

    if seconds_left <= 0:
        return 0.0

    seconds_per_year = (
        365.0 * 24.0 * 60.0 * 60.0
    )

    return (
        seconds_left / seconds_per_year
    )

import math


def normal_pdf(x):

    return (
        math.exp(
            -0.5 * x * x
        )
        / math.sqrt(
            2.0 * math.pi
        )
    )

def normal_cdf(x):
    return (
        0.5
        * (
            1.0
            + math.erf(
                x / math.sqrt(2.0)
            )
        )
    )


def black_scholes_price(
    spot,
    strike,
    time_to_expiration,
    risk_free_rate,
    implied_volatility,
    right
):

    if spot <= 0:
        return None

    if strike <= 0:
        return None

    if time_to_expiration <= 0:
        return None

    if implied_volatility <= 0:
        return None

    sigma_sqrt_t = (
        implied_volatility
        * math.sqrt(
            time_to_expiration
        )
    )

    if sigma_sqrt_t <= 0:
        return None

    d1 = (
        math.log(
            spot / strike
        )
        +
        (
            risk_free_rate
            +
            0.5
            * implied_volatility
            * implied_volatility
        )
        * time_to_expiration
    ) / sigma_sqrt_t

    d2 = (
        d1
        - sigma_sqrt_t
    )

    discount = math.exp(
        -risk_free_rate
        * time_to_expiration
    )

    right = right.upper()

    if right == "CALL":

        price = (
            spot
            * normal_cdf(d1)
            -
            strike
            * discount
            * normal_cdf(d2)
        )

    elif right == "PUT":

        price = (
            strike
            * discount
            * normal_cdf(-d2)
            -
            spot
            * normal_cdf(-d1)
        )

    else:
        return None

    return price

def implied_volatility_from_price(
    market_price,
    spot,
    strike,
    time_to_expiration,
    risk_free_rate,
    right
):

    if market_price is None:
        return None
    
    if pd.isna(market_price):
        return None

    if market_price <= 0:
        return None

    low_vol = 0.0001
    high_vol = 5.0

    for _ in range(100):

        mid_vol = (
            low_vol + high_vol
        ) / 2.0

        model_price = black_scholes_price(
            spot=spot,
            strike=strike,
            time_to_expiration=time_to_expiration,
            risk_free_rate=risk_free_rate,
            implied_volatility=mid_vol,
            right=right
        )

        if model_price is None:
            return None

        if abs(
            model_price - market_price
        ) < 0.0001:
            return mid_vol

        if model_price > market_price:
            high_vol = mid_vol
        else:
            low_vol = mid_vol

    return (
        low_vol + high_vol
    ) / 2.0

def black_scholes_gamma(
    spot,
    strike,
    time_to_expiration,
    risk_free_rate,
    implied_volatility
):

    if spot <= 0:
        return None

    if strike <= 0:
        return None

    if time_to_expiration <= 0:
        return None

    if implied_volatility <= 0:
        return None

    sigma_sqrt_t = (
        implied_volatility
        * math.sqrt(
            time_to_expiration
        )
    )

    if sigma_sqrt_t <= 0:
        return None

    d1 = (
        math.log(
            spot / strike
        )
        +
        (
            risk_free_rate
            +
            0.5
            * implied_volatility
            * implied_volatility
        )
        * time_to_expiration
    ) / sigma_sqrt_t

    gamma = (
        normal_pdf(d1)
        /
        (
            spot
            * sigma_sqrt_t
        )
    )

    return gamma


def black_scholes_delta(
    spot,
    strike,
    time_to_expiration,
    risk_free_rate,
    implied_volatility,
    right
):

    if spot <= 0:
        return None

    if strike <= 0:
        return None

    if time_to_expiration <= 0:
        return None

    if implied_volatility <= 0:
        return None

    sigma_sqrt_t = (
        implied_volatility
        * math.sqrt(
            time_to_expiration
        )
    )

    if sigma_sqrt_t <= 0:
        return None

    d1 = (
        math.log(
            spot / strike
        )
        +
        (
            risk_free_rate
            +
            0.5
            * implied_volatility
            * implied_volatility
        )
        * time_to_expiration
    ) / sigma_sqrt_t

    if right == "CALL":
        return normal_cdf(d1)

    if right == "PUT":
        return normal_cdf(d1) - 1.0

    return None


def get_spx_spot():

    load_dotenv(
        "tradestation_tokens.env",
        override=True
    )

    access_token = os.getenv(
        "TS_ACCESS_TOKEN"
    )

    headers = {
        "Authorization":
        f"Bearer {access_token}"
    }

    response = requests.get(
        TS_QUOTE_URL,
        headers=headers,
        timeout=10
    )

    # Si el token expiro,
    # renovarlo y volver a intentar
    if response.status_code == 401:

        access_token = (
            refresh_tradestation_token()
        )

        headers = {
            "Authorization":
            f"Bearer {access_token}"
        }

        response = requests.get(
            TS_QUOTE_URL,
            headers=headers,
            timeout=10
        )

    if response.status_code != 200:

        raise RuntimeError(
            f"TradeStation SPX error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    quotes = data.get(
        "Quotes",
        []
    )

    if not quotes:

        raise RuntimeError(
            "TradeStation no devolvio "
            "cotizacion SPX."
        )

    spx_quote = quotes[0]

    spx_last = float(
        spx_quote["Last"]
    )

    return spx_last

def is_history_window(now_et):
    start_minutes = (
        SAVE_START_HOUR * 60
        + SAVE_START_MINUTE
    )

    end_minutes = (
        SAVE_END_HOUR * 60
        + SAVE_END_MINUTE
    )

    current_minutes = (
        now_et.hour * 60
        + now_et.minute
    )

    return (
        start_minutes
        <= current_minutes
        <= end_minutes
    )

def is_signal_history_window(now_et):
    start_minutes = (
        SAVE_START_HOUR * 60
        + SAVE_START_MINUTE
    )

    end_minutes = (
        SIGNAL_HISTORY_END_HOUR * 60
        + SIGNAL_HISTORY_END_MINUTE
    )

    current_minutes = (
        now_et.hour * 60
        + now_et.minute
    )

    return (
        start_minutes
        <= current_minutes
        <= end_minutes
    )

def load_state():
    global DEALER_FLOW_POSITION
    global CONFIRMED_CALL_WALL
    global CONFIRMED_PUT_WALL
    global CONFIRMED_CALL_WALL_MISSES
    global CONFIRMED_PUT_WALL_MISSES
    global CURRENT_POSITION_STATE
    global CURRENT_POSITION_CONTRACTS
    global CURRENT_POSITION_ENTRY_SIDE
    global CURRENT_PENDING_ORDER_ACTION
    global CURRENT_PENDING_ORDER_SIDE
    global CURRENT_PENDING_ORDER_QUANTITY
    global CURRENT_PENDING_ORDER_SYMBOL
    global CURRENT_PENDING_ORDER_SUBMITTED_AT
    global LAST_DISPATCH_SIGNATURE
    global CURRENT_BROKER_ORDER_ID
    global CURRENT_BROKER_ORDER_STATUS
    global CURRENT_BROKER_ORDER_STATUS_DESCRIPTION
    global CURRENT_BROKER_ORDER_STATE

    if not os.path.exists(STATE_FILE):
        print("No existe estado previo. Se inicia desde cero.")
        return

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        state_date = state.get("date")
        today_date = datetime.now(MARKET_TZ).date().isoformat()

        if state_date != today_date:

            saved_broker_order_state = state.get(
                "broker_order_state",
                "NONE"
            )

            if saved_broker_order_state in (
                "OPEN",
                "UNKNOWN",
            ):
                CURRENT_BROKER_ORDER_ID = state.get(
                    "broker_order_id"
                )

                CURRENT_BROKER_ORDER_STATUS = state.get(
                    "broker_order_status",
                    "NONE"
                )

                CURRENT_BROKER_ORDER_STATUS_DESCRIPTION = state.get(
                    "broker_order_status_description",
                    "NONE"
                )

                CURRENT_BROKER_ORDER_STATE = (
                    saved_broker_order_state
                )

                CURRENT_PENDING_ORDER_ACTION = state.get(
                    "pending_order_action",
                    "NONE"
                )

                CURRENT_PENDING_ORDER_SIDE = state.get(
                    "pending_order_side",
                    "NONE"
                )

                CURRENT_PENDING_ORDER_QUANTITY = state.get(
                    "pending_order_quantity",
                    0
                )

                CURRENT_PENDING_ORDER_SYMBOL = state.get(
                    "pending_order_symbol"
                )

                CURRENT_PENDING_ORDER_SUBMITTED_AT = state.get(
                    "pending_order_submitted_at"
                )

                print(
                    "Estado previo de otra fecha | "
                    f"Orden broker pendiente preservada: "
                    f"{CURRENT_BROKER_ORDER_STATE}"
                )

            else:
                print(
                    "Estado previo corresponde a otra fecha. "
                    "Se inicia desde cero."
                )

            return

        required_fields = {
            "dealer_flow_position",
            "confirmed_call_wall",
            "confirmed_put_wall",
            "call_wall_misses",
            "put_wall_misses",
        }

        missing_fields = required_fields - state.keys()

        if missing_fields:
            print(
                f"Estado previo incompleto. Faltan campos: "
                f"{sorted(missing_fields)}. Se inicia desde cero."
            )
            return
        
    except Exception as e:
        print(f"No se pudo cargar el estado previo: {e}")
        return

    CONFIRMED_CALL_WALL = state.get("confirmed_call_wall")
    CONFIRMED_PUT_WALL = state.get("confirmed_put_wall")

    CONFIRMED_CALL_WALL_MISSES = int(
        state.get("call_wall_misses", 0)
    )

    CONFIRMED_PUT_WALL_MISSES = int(
        state.get("put_wall_misses", 0)
    )

    CURRENT_POSITION_STATE = state.get(
        "position_state",
        "FLAT"
    )

    CURRENT_POSITION_CONTRACTS = int(
        state.get("position_contracts", 0)
    )

    CURRENT_POSITION_ENTRY_SIDE = state.get(
        "position_entry_side",
        "NONE"
    )

    saved_dispatch_signature = state.get(
        "last_dispatch_signature"
    )

    if saved_dispatch_signature is None:
        LAST_DISPATCH_SIGNATURE = None
    else:
        LAST_DISPATCH_SIGNATURE = tuple(
            saved_dispatch_signature
        )

    CURRENT_BROKER_ORDER_ID = state.get(
        "broker_order_id"
    )

    CURRENT_BROKER_ORDER_STATUS = state.get(
        "broker_order_status",
        "NONE"
    )

    CURRENT_BROKER_ORDER_STATUS_DESCRIPTION = state.get(
        "broker_order_status_description",
        "NONE"
    )

    CURRENT_BROKER_ORDER_STATE = state.get(
        "broker_order_state",
        "NONE"
    )

    CURRENT_PENDING_ORDER_ACTION = state.get(
        "pending_order_action",
        "NONE"
    )

    CURRENT_PENDING_ORDER_SIDE = state.get(
        "pending_order_side",
        "NONE"
    )

    CURRENT_PENDING_ORDER_QUANTITY = state.get(
        "pending_order_quantity",
        0
    )

    CURRENT_PENDING_ORDER_SYMBOL = state.get(
        "pending_order_symbol"
    )

    CURRENT_PENDING_ORDER_SUBMITTED_AT = state.get(
        "pending_order_submitted_at"
    )

    position_valid, position_reason = validate_position_state()

    if not position_valid:
        print(
            f"Estado de posicion invalido: "
            f"{position_reason}. Se inicia FLAT."
        )

        CURRENT_POSITION_STATE = "FLAT"
        CURRENT_POSITION_CONTRACTS = 0
        CURRENT_POSITION_ENTRY_SIDE = "NONE"

    try:
        raw_positions = state.get("dealer_flow_position", {})

        DEALER_FLOW_POSITION = {}

        for key, value in raw_positions.items():
            symbol, expiration, strike, right = key.split("|")

            DEALER_FLOW_POSITION[
                (symbol, expiration, float(strike), right)
            ] = value

    except Exception as e:
        print(f"Estado dealer inválido. Se inicia desde cero: {e}")
        DEALER_FLOW_POSITION = {}
        return

    print(
        f"Estado previo cargado | "
        f"Call Wall: {CONFIRMED_CALL_WALL} | "
        f"Put Wall: {CONFIRMED_PUT_WALL} | "
        f"Posiciones dealer: {len(DEALER_FLOW_POSITION)}"
    )

def save_state():

    if OPEN_INTEREST_CACHE is not None:
        active_keys = set()

        for _, row in OPEN_INTEREST_CACHE.iterrows():
            active_keys.add(
                (
                    row["symbol"],
                    row["expiration"],
                    float(row["strike"]),
                    row["right"]
                )
            )

        stale_zero_keys = [
            key
            for key, value in DEALER_FLOW_POSITION.items()
            if key not in active_keys and value == 0
        ]

        for key in stale_zero_keys:
            del DEALER_FLOW_POSITION[key]

    serializable_positions = {}

    for key, value in DEALER_FLOW_POSITION.items():
        symbol, expiration, strike, right = key
        json_key = f"{symbol}|{expiration}|{strike}|{right}"
        serializable_positions[json_key] = value

    state = {
        "date": datetime.now(MARKET_TZ).date().isoformat(),
        "dealer_flow_position": serializable_positions,
        "confirmed_call_wall": CONFIRMED_CALL_WALL,
        "confirmed_put_wall": CONFIRMED_PUT_WALL,
        "call_wall_misses": CONFIRMED_CALL_WALL_MISSES,
        "put_wall_misses": CONFIRMED_PUT_WALL_MISSES,
        "call_wall_distance_points": CURRENT_CALL_WALL_DISTANCE,
        "put_wall_distance_points": CURRENT_PUT_WALL_DISTANCE,
        "wall_location": CURRENT_WALL_LOCATION,
        "position_state": CURRENT_POSITION_STATE,
        "position_contracts": CURRENT_POSITION_CONTRACTS,
        "position_entry_side": CURRENT_POSITION_ENTRY_SIDE,
        "last_dispatch_signature": LAST_DISPATCH_SIGNATURE,
        "broker_order_id": CURRENT_BROKER_ORDER_ID,
        "broker_order_status": CURRENT_BROKER_ORDER_STATUS,
        "broker_order_status_description": CURRENT_BROKER_ORDER_STATUS_DESCRIPTION,
        "broker_order_state": CURRENT_BROKER_ORDER_STATE,
        "pending_order_action": CURRENT_PENDING_ORDER_ACTION,
        "pending_order_side": CURRENT_PENDING_ORDER_SIDE,
        "pending_order_quantity": CURRENT_PENDING_ORDER_QUANTITY,
        "pending_order_symbol": CURRENT_PENDING_ORDER_SYMBOL,
        "pending_order_submitted_at": CURRENT_PENDING_ORDER_SUBMITTED_AT,
    }

    temp_state_file = STATE_FILE + ".tmp"

    with open(temp_state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    os.replace(temp_state_file, STATE_FILE)    

def create_client():
    print("Conectando con ThetaData...")

    load_dotenv("thetadata.env", override=True)

    while True:
        try:
            client = ThetaClient(
                dataframe_type="pandas"
            )

            print("Cliente ThetaData creado.")
            return client

        except KeyboardInterrupt:
            print(
                "\nPrograma detenido por el usuario "
                "durante la conexion con ThetaData."
            )
            return None

        except Exception as e:
            print(
                f"Error conectando con ThetaData: {e}"
            )
            print("Reintentando en 5 segundos...")
            time.sleep(5)


# ============================================================
# OBTENER SNAPSHOT LIVE
# ============================================================
def get_live_snapshot(client):

    global OPEN_INTEREST_CACHE
    global DEALER_FLOW_POSITION

    now_et = datetime.now(MARKET_TZ)

    # SPXW 0DTE = expiracion de hoy
    expiration = now_et.date()

    # --------------------------------------------------------
    # TRADE SNAPSHOT
    # --------------------------------------------------------

    trades = client.option_snapshot_trade(
        symbol=SYMBOL,
        expiration=expiration,
        strike="*",
        right="both",
        strike_range=STRIKE_RANGE
    )

    trades = trades[
        [
            "symbol",
            "expiration",
            "strike",
            "right",
            "timestamp",
            "price",
            "size"
        ]
    ].copy()

    trades = trades.rename(
        columns={
            "timestamp": "trade_time",
            "price": "last",
            "size": "last_size"
        }
    )

    # --------------------------------------------------------
    # OPEN INTEREST SNAPSHOT
    # --------------------------------------------------------

    if OPEN_INTEREST_CACHE is None:

        OPEN_INTEREST_CACHE = client.option_snapshot_open_interest(
            symbol=SYMBOL,
            expiration=expiration,
            strike="*",
            right="both",
            strike_range=OI_STRIKE_RANGE
        )

        OPEN_INTEREST_CACHE = OPEN_INTEREST_CACHE[
            [
                "symbol",
                "expiration",
                "strike",
                "right",
                "open_interest"
            ]
        ].copy()

    open_interest = OPEN_INTEREST_CACHE.copy()
        
    # --------------------------------------------------------
    # QUOTE SNAPSHOT
    # --------------------------------------------------------

    quotes = client.option_snapshot_quote(
        symbol=SYMBOL,
        expiration=expiration,
        strike="*",
        right="both",
        strike_range=STRIKE_RANGE
    )

    quotes = quotes[
        [
            "symbol",
            "expiration",
            "strike",
            "right",
            "timestamp",
            "bid",
            "bid_size",
            "ask",
            "ask_size"
        ]
    ].copy()

    quotes = quotes.rename(
        columns={
            "timestamp": "quote_time"
        }
    )
    
    # --------------------------------------------------------
    # COMBINAR TRADE + QUOTE
    # --------------------------------------------------------

    df = pd.merge(
        trades,
        quotes,
        on=[
            "symbol",
            "expiration",
            "strike",
            "right"
        ],
        how="outer"
    )

    df = pd.merge(
        open_interest,
        df,
        on=[
            "symbol",
            "expiration",
            "strike",
            "right"
        ],
        how="left"
    )

    # --------------------------------------------------------
    # CALCULOS
    # --------------------------------------------------------

    df["mid"] = (
        df["bid"] + df["ask"]
    ) / 2

    df["spread"] = (
        df["ask"] - df["bid"]
    )

    def classify_trade(row):

        last = row["last"]
        bid = row["bid"]
        ask = row["ask"]
        mid = row["mid"]

        if pd.isna(last) or pd.isna(bid) or pd.isna(ask):
            return "UNKNOWN"

        if ask <= bid:
            return "UNKNOWN"

        distance_to_ask = abs(last - ask)
        distance_to_bid = abs(last - bid)
        distance_to_mid = abs(last - mid)

        if (
            distance_to_ask < distance_to_bid
            and distance_to_ask < distance_to_mid
        ):
            return "BUYER_AGGRESSOR"

        if (
            distance_to_bid < distance_to_ask
            and distance_to_bid < distance_to_mid
        ):
            return "SELLER_AGGRESSOR"

        return "NEUTRAL"

    df["trade_class"] = df.apply(
        classify_trade,
        axis=1
    )

    df["is_new_trade"] = df.apply(
        mark_new_trade,
        axis=1
    )
    
    # --------------------------------------------------------
    # IV + GAMMA + GEX
    # --------------------------------------------------------

    spx_spot = get_spx_spot()

    # Refrescar la hora despues de descargar los datos
    now_et = datetime.now(MARKET_TZ)

    time_to_expiration = get_time_to_expiration(
        now_et
    )

    df["implied_volatility"] = df.apply(
        lambda row: implied_volatility_from_price(
            market_price=row["mid"],
            spot=spx_spot,
            strike=row["strike"],
            time_to_expiration=time_to_expiration,
            risk_free_rate=RISK_FREE_RATE,
            right=row["right"]
        ),
        axis=1
    )

    df["gamma"] = df.apply(
        lambda row: black_scholes_gamma(
            spot=spx_spot,
            strike=row["strike"],
            time_to_expiration=time_to_expiration,
            risk_free_rate=RISK_FREE_RATE,
            implied_volatility=row["implied_volatility"]
        )
        if row["implied_volatility"] is not None
        else None,
        axis=1
    )

    df["delta"] = df.apply(
        lambda row: black_scholes_delta(
            spot=spx_spot,
            strike=row["strike"],
            time_to_expiration=time_to_expiration,
            risk_free_rate=RISK_FREE_RATE,
            implied_volatility=row["implied_volatility"],
            right=row["right"]
        )
        if row["implied_volatility"] is not None
        else None,
        axis=1
    )

    df["gex_abs"] = (
        df["gamma"]
        * df["open_interest"]
        * 100
        * spx_spot
        * spx_spot
        * 0.01
    )

    df["gex_abs"] = (
        df["gex_abs"].fillna(0.0)
    )

    df["spx_spot"] = spx_spot

    # Edad del ultimo trade
    if "trade_time" in df.columns:

        df["trade_age_sec"] = (
            now_et
            - pd.to_datetime(
                df["trade_time"]
            )
        ).dt.total_seconds()

    df["is_fresh_trade"] = (
        df["is_new_trade"]
        & df["trade_age_sec"].ge(
            -TRADE_FUTURE_TOLERANCE_SECONDS
        )
        & df["trade_age_sec"].le(
            TRADE_MAX_AGE_SECONDS
        )
    )

    def estimate_dealer_flow(row):

        if not row["is_fresh_trade"]:
            return 0

        if row["trade_class"] == "BUYER_AGGRESSOR":
            return -1

        if row["trade_class"] == "SELLER_AGGRESSOR":
            return 1

        return 0

    df["dealer_flow_sign"] = df.apply(
        estimate_dealer_flow,
        axis=1
    )

    df["dealer_flow_contracts"] = (
        df["dealer_flow_sign"]
        * df["last_size"].fillna(0)
    )

    df["dealer_delta_notional"] = (
        df["delta"].fillna(0.0)
        * df["dealer_flow_contracts"]
        * 100
        * spx_spot
    )

    df["dealer_hedge_notional"] = (
        -df["dealer_delta_notional"]
    )

    def update_dealer_flow_position(row):
        key = (
            row["symbol"],
            row["expiration"],
            row["strike"],
            row["right"]
        )

        previous_position = DEALER_FLOW_POSITION.get(key, 0)

        new_position = (
            previous_position
            + row["dealer_flow_contracts"]
        )

        DEALER_FLOW_POSITION[key] = new_position

        return new_position


    df["dealer_flow_position"] = df.apply(
        update_dealer_flow_position,
        axis=1
    )

    df["dealer_dynamic_gex"] = (
        df["gamma"]
        * df["dealer_flow_position"]
        * 100
        * spx_spot
        * spx_spot
        * 0.01
    )

    df["dealer_dynamic_gex"] = (
        df["dealer_dynamic_gex"].fillna(0.0)
    )

    df["dealer_flow_gex"] = (
        df["gamma"]
        * df["dealer_flow_contracts"]
        * 100
        * spx_spot
        * spx_spot
        * 0.01
    )

    df["dealer_flow_gex"] = (
        df["dealer_flow_gex"].fillna(0.0)
    )

    dynamic_gex_by_strike = (
        df.groupby(
            ["strike", "right"],
            as_index=False
        )["dealer_dynamic_gex"]
        .sum()
    )

    oi_by_strike = (
        df.groupby(
            ["strike", "right"],
            as_index=False
        )["open_interest"]
        .sum()
    )

    dynamic_gex_by_strike = pd.merge(
        dynamic_gex_by_strike,
        oi_by_strike,
        on=[
            "strike",
            "right"
        ],
        how="left"
    )

    # Edad del quote
    if "quote_time" in df.columns:

        df["quote_age_sec"] = (
            now_et
            - pd.to_datetime(
                df["quote_time"]
            )
        ).dt.total_seconds()

    # Ordenar por strike y CALL/PUT
    df = df.sort_values(
        by=[
            "strike",
            "right"
        ]
    ).reset_index(
        drop=True
    )

    return df, now_et

def evaluate_risk_parameters(
    position_size_contracts,
    stop_loss_points,
    take_profit_points,
    max_loss_usd
):

    parameters = {
        "POSITION SIZE": position_size_contracts,
        "STOP LOSS": stop_loss_points,
        "TAKE PROFIT": take_profit_points,
        "MAX LOSS": max_loss_usd
    }

    missing_parameters = [
        name
        for name, value in parameters.items()
        if value is None
    ]

    if missing_parameters:

        return (
            "BLOCKED",
            False,
            "MISSING RISK PARAMETERS: "
            + ", ".join(missing_parameters)
        )

    position_size_valid = (
        isinstance(
            position_size_contracts,
            int
        )
        and not isinstance(
            position_size_contracts,
            bool
        )
        and position_size_contracts > 0
    )

    numeric_parameters = {
        "STOP LOSS": stop_loss_points,
        "TAKE PROFIT": take_profit_points,
        "MAX LOSS": max_loss_usd
    }

    invalid_parameters = []

    if not position_size_valid:
        invalid_parameters.append(
            "POSITION SIZE"
        )

    for name, value in numeric_parameters.items():

        value_valid = (
            isinstance(
                value,
                (int, float)
            )
            and not isinstance(
                value,
                bool
            )
            and math.isfinite(
                float(value)
            )
            and value > 0
        )

        if not value_valid:
            invalid_parameters.append(
                name
            )

    if invalid_parameters:

        return (
            "BLOCKED",
            False,
            "INVALID RISK PARAMETERS: "
            + ", ".join(invalid_parameters)
        )

    expected_max_loss_usd = (
        position_size_contracts
        * stop_loss_points
        * ES_POINT_VALUE_USD
    )

    if not math.isclose(
        max_loss_usd,
        expected_max_loss_usd,
        rel_tol=0.0,
        abs_tol=0.01
    ):

        return (
            "BLOCKED",
            False,
            "MAX LOSS DOES NOT MATCH "
            "POSITION SIZE x STOP LOSS x ES POINT VALUE"
        )

    return (
        "READY",
        True,
        "RISK PARAMETERS VALIDATED"
    )    


# ============================================================
# MOSTRAR TABLA
# ============================================================

def display_snapshot(df, now_et):

    global LAST_DYNAMIC_CALL_WALL
    global LAST_DYNAMIC_PUT_WALL
    global CALL_WALL_STREAK
    global PUT_WALL_STREAK
    global CONFIRMED_CALL_WALL
    global CONFIRMED_PUT_WALL
    global CONFIRMED_CALL_WALL_MISSES
    global CONFIRMED_PUT_WALL_MISSES
    global CURRENT_GAMMA_BALANCE
    global CURRENT_GAMMA_REGIME
    global CURRENT_NET_DYNAMIC_GEX
    global CURRENT_POSITIVE_DYNAMIC_GEX
    global CURRENT_NEGATIVE_DYNAMIC_GEX
    global CURRENT_DEALER_FLOW_GEX
    global CURRENT_DEALER_DYNAMIC_GEX
    global CURRENT_DEALER_DELTA_NOTIONAL
    global CURRENT_DEALER_HEDGE_NOTIONAL
    global CURRENT_ABS_HEDGE_NOTIONAL
    global CURRENT_HEDGE_PRESSURE_BALANCE
    global CURRENT_HEDGE_PRESSURE
    global CURRENT_DIRECTIONAL_BIAS
    global CURRENT_COMBINED_MARKET_STATE
    global CURRENT_CALL_WALL_DISTANCE
    global CURRENT_PUT_WALL_DISTANCE
    global CURRENT_WALL_LOCATION
    global CURRENT_WALL_CONTEXT
    global CURRENT_FULL_MARKET_CONTEXT
    global CURRENT_SIGNAL_CANDIDATE
    global CURRENT_SIGNAL_REASON
    global CURRENT_SETUP_QUALITY
    global LAST_ACTIONABLE_SIGNAL_CANDIDATE
    global CURRENT_SIGNAL_CANDIDATE_STREAK
    global CURRENT_CONFIRMED_SIGNAL
    global CURRENT_SIGNAL_CONFIRMED
    global CURRENT_RISK_STATUS
    global CURRENT_RISK_PERMISSION
    global CURRENT_RISK_REASON
    global CURRENT_ENTRY_EXECUTION_PERMISSION
    global CURRENT_EXIT_EXECUTION_PERMISSION
    global CURRENT_EXECUTION_SAFETY_OK
    global CURRENT_EXECUTION_SAFETY_REASON
    global CURRENT_DISPATCH_STATUS
    global CURRENT_DISPATCH_REASON
    global CURRENT_DISPATCH_ID
    global CURRENT_BROKER_ORDER_ID
    global CURRENT_BROKER_ORDER_STATUS
    global CURRENT_BROKER_ORDER_STATUS_DESCRIPTION
    global CURRENT_BROKER_ORDER_STATE
    global CURRENT_POSITION_STATE
    global CURRENT_POSITION_CONTRACTS
    global CURRENT_POSITION_ENTRY_SIDE
    global CURRENT_POSITION_VALID
    global CURRENT_POSITION_VALIDATION_REASON
    global CURRENT_FRESH_TRADES
    global CURRENT_NEW_TRADES
    global CURRENT_REJECTED_TRADES
    global CURRENT_NEW_TRADE_AGE_MIN_SEC
    global CURRENT_NEW_TRADE_AGE_MAX_SEC
    global CURRENT_TEMPORAL_ACCEPTANCE_RATIO
    global CURRENT_TEMPORAL_QUALITY
    global CURRENT_FLOW_DATA_STATUS
    global CURRENT_FLOW_USABLE
    global CURRENT_FORCED_EXIT_REQUIRED
    global CURRENT_TRADING_STATUS
    global CURRENT_OPERATIONAL_MODE
    global CURRENT_SIGNAL_PERMISSION
    global CURRENT_OPERATIONAL_REASON
    global CURRENT_DEALER_SELL_OPTIONS
    global CURRENT_DEALER_BUY_OPTIONS
    global CURRENT_NEUTRAL_TRADES
    global CURRENT_CLASSIFIED_TRADE_RATIO
    global CURRENT_NEUTRAL_TRADE_RATIO
    global LAST_FRESH_TRADE_CYCLE_TIME
    global CURRENT_FRESH_TRADE_AGE_SEC
    global CURRENT_FLOW_FRESHNESS

    (
        CURRENT_RISK_STATUS,
        CURRENT_RISK_PERMISSION,
        CURRENT_RISK_REASON
    ) = evaluate_risk_parameters(
        position_size_contracts=(
            CURRENT_POSITION_SIZE_CONTRACTS
        ),
        stop_loss_points=(
            CURRENT_STOP_LOSS_POINTS
        ),
        take_profit_points=(
            CURRENT_TAKE_PROFIT_POINTS
        ),
        max_loss_usd=(
            CURRENT_MAX_LOSS_USD
        )
    )

    CURRENT_ENTRY_EXECUTION_PERMISSION = False
    CURRENT_EXIT_EXECUTION_PERMISSION = False

    os.system(
        "cls"
        if os.name == "nt"
        else "clear"
    )

    print("=" * 140)

    print(
        f"SPXW 0DTE LIVE | "
        f"{now_et.strftime('%Y-%m-%d %H:%M:%S')} ET"
    )

    print("=" * 140)

    display_cols = [
        "strike",
        "right",
        "open_interest",
        "last",
        "last_size",
        "bid",
        "bid_size",
        "ask",
        "ask_size",
        "mid",
        "spread"
    ]

    df_display = df[
        display_cols
    ].copy()

    for col in [
        "strike",
        "last",
        "bid",
        "ask",
        "mid",
        "spread"
    ]:

        df_display[col] = pd.to_numeric(
            df_display[col],
            errors="coerce"
        ).round(3)

    print(
        df_display.to_string(
            index=False
        )
    )

    print(
        "\n" + "=" * 140
    )

    print(
        f"Contratos: {len(df)} | "
        f"Actualizacion cada "
        f"{REFRESH_SECONDS} segundos"
    )

    print(
        "Datos: Trade + Trade Size + "
        "Bid + Ask + Bid Size + Ask Size"
    )

    print(
    f"Historico diario: {HISTORY_FOLDER}"
    )

    print(
    f"Trades frescos detectados: "
    f"{int(df['is_fresh_trade'].sum())}"
    )

    CURRENT_FRESH_TRADES = int(
        df["is_fresh_trade"].sum()
    )

    if CURRENT_FRESH_TRADES > 0:
        LAST_FRESH_TRADE_CYCLE_TIME = now_et.isoformat()

    if LAST_FRESH_TRADE_CYCLE_TIME is not None:
        last_fresh_dt = datetime.fromisoformat(
            LAST_FRESH_TRADE_CYCLE_TIME
        )

        CURRENT_FRESH_TRADE_AGE_SEC = (
            now_et - last_fresh_dt
        ).total_seconds()
    else:
        CURRENT_FRESH_TRADE_AGE_SEC = None

    if CURRENT_FRESH_TRADE_AGE_SEC is None:
        CURRENT_FLOW_FRESHNESS = "NO DATA"
    elif CURRENT_FRESH_TRADE_AGE_SEC <= 10:
        CURRENT_FLOW_FRESHNESS = "FRESH"
    elif CURRENT_FRESH_TRADE_AGE_SEC <= 30:
        CURRENT_FLOW_FRESHNESS = "AGING"
    else:
        CURRENT_FLOW_FRESHNESS = "STALE"

    print(
        f"Trades nuevos detectados: "
        f"{int(df['is_new_trade'].sum())}"
    )

    CURRENT_REJECTED_TRADES = int(
        (
            df["is_new_trade"]
            & ~df["is_fresh_trade"]
        ).sum()
    )

    print(
        f"Trades rechazados por tiempo: "
        f"{CURRENT_REJECTED_TRADES}"
    )

    new_trade_ages = df.loc[
        df["is_new_trade"],
        "trade_age_sec"
    ].dropna()

    if not new_trade_ages.empty:
        CURRENT_NEW_TRADE_AGE_MIN_SEC = float(
            new_trade_ages.min()
        )
        CURRENT_NEW_TRADE_AGE_MAX_SEC = float(
            new_trade_ages.max()
        )

        print(
            f"Edad trades nuevos | min: "
            f"{CURRENT_NEW_TRADE_AGE_MIN_SEC:.1f}s | "
            f"max: {CURRENT_NEW_TRADE_AGE_MAX_SEC:.1f}s"
        )
    else:
        CURRENT_NEW_TRADE_AGE_MIN_SEC = None
        CURRENT_NEW_TRADE_AGE_MAX_SEC = None

        print(
            "Edad trades nuevos | SIN TRADES NUEVOS"
        )

    print(f"Flow Freshness: {CURRENT_FLOW_FRESHNESS}")

    CURRENT_NEW_TRADES = int(
        df["is_new_trade"].sum()
    )

    if CURRENT_NEW_TRADES > 0:
        CURRENT_TEMPORAL_ACCEPTANCE_RATIO = (
            CURRENT_FRESH_TRADES
            / CURRENT_NEW_TRADES
        )

        if CURRENT_TEMPORAL_ACCEPTANCE_RATIO >= 0.90:
            CURRENT_TEMPORAL_QUALITY = "HEALTHY"
        elif CURRENT_TEMPORAL_ACCEPTANCE_RATIO >= 0.70:
            CURRENT_TEMPORAL_QUALITY = "DEGRADED"
        else:
            CURRENT_TEMPORAL_QUALITY = "UNRELIABLE"
    else:
        CURRENT_TEMPORAL_ACCEPTANCE_RATIO = 0.0
        CURRENT_TEMPORAL_QUALITY = "NO NEW TRADES"

    print(
        f"Calidad temporal: "
        f"{CURRENT_TEMPORAL_QUALITY} | "
        f"Aceptacion: "
        f"{CURRENT_TEMPORAL_ACCEPTANCE_RATIO:.1%}"
    )

    if (
        CURRENT_FLOW_FRESHNESS in ("NO DATA", "STALE")
        or CURRENT_TEMPORAL_QUALITY == "UNRELIABLE"
    ):
        CURRENT_FLOW_DATA_STATUS = "BLOCKED"
        CURRENT_FLOW_USABLE = False

    elif (
        CURRENT_FLOW_FRESHNESS == "AGING"
        or CURRENT_TEMPORAL_QUALITY == "DEGRADED"
    ):
        CURRENT_FLOW_DATA_STATUS = "CAUTION"
        CURRENT_FLOW_USABLE = False

    else:
        CURRENT_FLOW_DATA_STATUS = "RELIABLE"
        CURRENT_FLOW_USABLE = True

    print(
        f"Flow Data Status: "
        f"{CURRENT_FLOW_DATA_STATUS} | "
        f"Usable: {CURRENT_FLOW_USABLE}"
    )

    print(
        f"Trade age | min: "
        f"{df['trade_age_sec'].min():.1f}s | "
        f"max: {df['trade_age_sec'].max():.1f}s"
        )

    buyer_aggressor = int(
    (df["dealer_flow_sign"] == -1).sum()
    )

    seller_aggressor = int(
    (df["dealer_flow_sign"] == 1).sum()
    )

    CURRENT_DEALER_SELL_OPTIONS = buyer_aggressor
    CURRENT_DEALER_BUY_OPTIONS = seller_aggressor

    CURRENT_NEUTRAL_TRADES = int(
        CURRENT_FRESH_TRADES
        - CURRENT_DEALER_SELL_OPTIONS
        - CURRENT_DEALER_BUY_OPTIONS
    )

    if CURRENT_FRESH_TRADES > 0:
        CURRENT_CLASSIFIED_TRADE_RATIO = (
            (
                CURRENT_DEALER_SELL_OPTIONS
                + CURRENT_DEALER_BUY_OPTIONS
            )
            / CURRENT_FRESH_TRADES
        )
    else:
        CURRENT_CLASSIFIED_TRADE_RATIO = 0.0

    if CURRENT_FRESH_TRADES > 0:
        CURRENT_NEUTRAL_TRADE_RATIO = (
            CURRENT_NEUTRAL_TRADES
            / CURRENT_FRESH_TRADES
        )
    else:
        CURRENT_NEUTRAL_TRADE_RATIO = 0.0

    print(
    f"Dealer flow estimado | "
    f"Dealer vende opciones: {buyer_aggressor} | "
    f"Dealer compra opciones: {seller_aggressor}"
    )

    dealer_flow_gex_total = df["dealer_flow_gex"].fillna(0).sum()

    CURRENT_DEALER_FLOW_GEX = float(dealer_flow_gex_total)

    print(
        f"Dealer Flow GEX total: "
        f"${dealer_flow_gex_total:,.0f}"
    )

    dealer_delta_notional_total = (
        df["dealer_delta_notional"]
        .fillna(0)
        .sum()
    )

    dealer_hedge_notional_total = (
        df["dealer_hedge_notional"]
        .fillna(0)
        .sum()
    )

    CURRENT_DEALER_DELTA_NOTIONAL = float(
        dealer_delta_notional_total
    )

    CURRENT_DEALER_HEDGE_NOTIONAL = float(
        dealer_hedge_notional_total
    )

    abs_hedge_notional_total = (
        df["dealer_hedge_notional"]
        .fillna(0)
        .abs()
        .sum()
    )

    CURRENT_ABS_HEDGE_NOTIONAL = float(
        abs_hedge_notional_total
    )

    if abs_hedge_notional_total > 0:
        hedge_pressure_balance = (
            dealer_hedge_notional_total
            / abs_hedge_notional_total
        )
    else:
        hedge_pressure_balance = 0.0

    CURRENT_HEDGE_PRESSURE_BALANCE = float(
        hedge_pressure_balance
    )

    if not CURRENT_FLOW_USABLE:
        hedge_pressure = "BLOCKED"
    elif abs_hedge_notional_total <= 0:
        hedge_pressure = "NO DATA"
    elif abs_hedge_notional_total < MIN_ABS_HEDGE_NOTIONAL:
        hedge_pressure = "LOW ACTIVITY"
    elif hedge_pressure_balance >= 0.50:
        hedge_pressure = "BUY PRESSURE STRONG"
    elif hedge_pressure_balance >= 0.20:
        hedge_pressure = "BUY PRESSURE"
    elif hedge_pressure_balance <= -0.50:
        hedge_pressure = "SELL PRESSURE STRONG"
    elif hedge_pressure_balance <= -0.20:
        hedge_pressure = "SELL PRESSURE"
    else:
        hedge_pressure = "NEUTRAL / MIXED"

    CURRENT_HEDGE_PRESSURE = hedge_pressure

    print(
        f"Dealer Delta Notional nuevos: "
        f"${dealer_delta_notional_total:,.0f}"
    )

    print(
        f"Dealer Hedge Notional nuevos: "
        f"${dealer_hedge_notional_total:,.0f}"
    )

    print(
        f"Absolute Hedge Notional nuevos: "
        f"${abs_hedge_notional_total:,.0f}"
    )

    print(
        f"Minimum Absolute Hedge Notional: "
        f"${MIN_ABS_HEDGE_NOTIONAL:,.0f}"
    )

    print(
        f"Hedge Pressure Balance: "
        f"{hedge_pressure_balance:+.3f}"
    )
    print(
        f"Dealer Hedge Pressure: "
        f"{hedge_pressure}"
    )

    dealer_dynamic_gex_total = df["dealer_dynamic_gex"].fillna(0).sum()

    CURRENT_DEALER_DYNAMIC_GEX = float(dealer_dynamic_gex_total)

    print(
        f"Dealer Dynamic GEX acumulado: "
        f"${dealer_dynamic_gex_total:,.0f}"
    )

    dynamic_gex_by_strike = (
        df.groupby(
            ["strike", "right"],
            as_index=False
        )["dealer_dynamic_gex"]
        .sum()
    )

    oi_by_strike = (
        df.groupby(
            ["strike", "right"],
            as_index=False
        )["open_interest"]
        .sum()
    )

    dynamic_gex_by_strike = pd.merge(
        dynamic_gex_by_strike,
        oi_by_strike,
        on=["strike", "right"],
        how="left"
    )

    dynamic_gex_by_strike["gex_positive"] = (
        dynamic_gex_by_strike["dealer_dynamic_gex"].clip(lower=0)
    )

    dynamic_gex_by_strike["gex_negative"] = (
        dynamic_gex_by_strike["dealer_dynamic_gex"].clip(upper=0)
    )

    total_positive_gex = dynamic_gex_by_strike["gex_positive"].sum()
    total_negative_gex = dynamic_gex_by_strike["gex_negative"].sum()

    CURRENT_POSITIVE_DYNAMIC_GEX = float(total_positive_gex)
    CURRENT_NEGATIVE_DYNAMIC_GEX = float(total_negative_gex)

    total_abs_gex = (
        total_positive_gex
        + abs(total_negative_gex)
    )

    net_dynamic_gex = (
        total_positive_gex
        + total_negative_gex
    )

    CURRENT_NET_DYNAMIC_GEX = float(net_dynamic_gex)

    if total_abs_gex > 0:
        gamma_balance = (
            net_dynamic_gex
            / total_abs_gex
        )
    else:
        gamma_balance = 0

    print(
        f"Gamma Balance: "
        f"{gamma_balance:+.3f}"
    )

    if gamma_balance >= 0.50:
        gamma_regime = "POSITIVE GAMMA STRONG"
    elif gamma_balance >= 0.20:
        gamma_regime = "POSITIVE GAMMA"
    elif gamma_balance <= -0.50:
        gamma_regime = "NEGATIVE GAMMA STRONG"
    elif gamma_balance <= -0.20:
        gamma_regime = "NEGATIVE GAMMA"
    else:
        gamma_regime = "NEUTRAL / MIXED"

    CURRENT_GAMMA_BALANCE = float(gamma_balance)
    CURRENT_GAMMA_REGIME = gamma_regime

    print(
        f"Dynamic Gamma Regime: "
        f"{gamma_regime}"
    )

    current_market_minutes = (
        now_et.hour * 60
        + now_et.minute
    )

    forced_exit_minutes = (
        FORCED_EXIT_HOUR * 60
        + FORCED_EXIT_MINUTE
    )

    CURRENT_FORCED_EXIT_REQUIRED = (
        current_market_minutes
        >= forced_exit_minutes
    )

    CURRENT_TRADING_STATUS = (
        "FORCED EXIT"
        if CURRENT_FORCED_EXIT_REQUIRED
        else "ACTIVE"
    )

    print(
        f"Trading Status: "
        f"{CURRENT_TRADING_STATUS} | "
        f"Forced Exit 15:30 ET"
    )

    if CURRENT_FORCED_EXIT_REQUIRED:

        CURRENT_OPERATIONAL_MODE = "FORCED EXIT"
        CURRENT_SIGNAL_PERMISSION = False
        CURRENT_OPERATIONAL_REASON = (
            "FORCED EXIT REQUIRED AT 15:30 ET"
        )

    elif not CURRENT_FLOW_USABLE:

        CURRENT_OPERATIONAL_MODE = "BLOCKED"
        CURRENT_SIGNAL_PERMISSION = False
        CURRENT_OPERATIONAL_REASON = (
            f"FLOW DATA {CURRENT_FLOW_DATA_STATUS}"
        )

    elif gamma_regime == "POSITIVE GAMMA STRONG":

        CURRENT_OPERATIONAL_MODE = "MEAN REVERSION STRONG"
        CURRENT_SIGNAL_PERMISSION = True
        CURRENT_OPERATIONAL_REASON = (
            "DEALER HEDGING FAVORS STRONG MEAN REVERSION"
        )

    elif gamma_regime == "POSITIVE GAMMA":

        CURRENT_OPERATIONAL_MODE = "MEAN REVERSION"
        CURRENT_SIGNAL_PERMISSION = True
        CURRENT_OPERATIONAL_REASON = (
            "DEALER HEDGING FAVORS MEAN REVERSION"
        )

    elif gamma_regime == "NEGATIVE GAMMA STRONG":

        CURRENT_OPERATIONAL_MODE = "VOLATILITY EXPANSION STRONG"
        CURRENT_SIGNAL_PERMISSION = True
        CURRENT_OPERATIONAL_REASON = (
            "DEALER HEDGING FAVORS STRONG VOLATILITY EXPANSION"
        )

    elif gamma_regime == "NEGATIVE GAMMA":

        CURRENT_OPERATIONAL_MODE = "VOLATILITY EXPANSION"
        CURRENT_SIGNAL_PERMISSION = True
        CURRENT_OPERATIONAL_REASON = (
            "DEALER HEDGING FAVORS VOLATILITY EXPANSION"
        )

    else:

        CURRENT_OPERATIONAL_MODE = "NEUTRAL / WAIT"
        CURRENT_SIGNAL_PERMISSION = False
        CURRENT_OPERATIONAL_REASON = (
            "NO CLEAR DYNAMIC GAMMA EDGE"
        )

    print(
        f"Operational Mode: "
        f"{CURRENT_OPERATIONAL_MODE}"
    )

    print(
        f"Signal Permission: "
        f"{CURRENT_SIGNAL_PERMISSION}"
    )

    print(
        f"Operational Reason: "
        f"{CURRENT_OPERATIONAL_REASON}"
    )

    if not CURRENT_FLOW_USABLE:
        directional_bias = "BLOCKED"
    elif hedge_pressure == "BUY PRESSURE STRONG":
        directional_bias = "BULLISH STRONG"
    elif hedge_pressure == "BUY PRESSURE":
        directional_bias = "BULLISH"
    elif hedge_pressure == "SELL PRESSURE STRONG":
        directional_bias = "BEARISH STRONG"
    elif hedge_pressure == "SELL PRESSURE":
        directional_bias = "BEARISH"
    else:
        directional_bias = "NEUTRAL"

    CURRENT_DIRECTIONAL_BIAS = directional_bias

    if directional_bias == "BLOCKED":
        combined_market_state = "BLOCKED"
    else:
        combined_market_state = (
            f"{directional_bias} | "
            f"{CURRENT_OPERATIONAL_MODE}"
        )

    CURRENT_COMBINED_MARKET_STATE = (
        combined_market_state
    )

    print(
        f"Directional Bias: "
        f"{CURRENT_DIRECTIONAL_BIAS}"
    )

    print(
        f"Combined Market State: "
        f"{CURRENT_COMBINED_MARKET_STATE}"
    )

    print(
        f"\nDynamic GEX positivo total: "   
        f"${total_positive_gex:,.0f}"
    )

    print(
        f"Dynamic GEX negativo total: "
        f"${total_negative_gex:,.0f}"
    )

    print("\nDynamic GEX por strike:")
    
    current_spot = df["spx_spot"].dropna().iloc[0]

    dynamic_gex_by_strike["abs_gex_raw"] = (
        dynamic_gex_by_strike["dealer_dynamic_gex"].abs()
    )

    dynamic_gex_by_strike["max_abs_gex_side"] = (
        dynamic_gex_by_strike
        .groupby("right")["abs_gex_raw"]
        .transform("max")
    )

    dynamic_gex_by_strike["max_oi_side"] = (
        dynamic_gex_by_strike
        .groupby("right")["open_interest"]
        .transform("max")
    )

    dynamic_gex_by_strike["gex_score"] = (
        dynamic_gex_by_strike["abs_gex_raw"]
        / dynamic_gex_by_strike["max_abs_gex_side"].replace(0, 1)
    )

    dynamic_gex_by_strike["oi_score"] = (
        dynamic_gex_by_strike["open_interest"]
        / dynamic_gex_by_strike["max_oi_side"].replace(0, 1)
    )
    
    dynamic_gex_by_strike["distance_from_spot"] = (
        dynamic_gex_by_strike["strike"]
        - current_spot
    )

    dynamic_gex_by_strike["distance_abs"] = (
        dynamic_gex_by_strike["distance_from_spot"].abs()
    )

    dynamic_gex_by_strike["distance_score"] = (
        dynamic_gex_by_strike["distance_abs"]
        / dynamic_gex_by_strike["distance_abs"].max()
    )
    
    dynamic_gex_by_strike = (
        dynamic_gex_by_strike
        .sort_values(["right", "strike"])
        .reset_index(drop=True)
    )

    dynamic_gex_by_strike["abs_gex"] = (
        dynamic_gex_by_strike["dealer_dynamic_gex"].abs()
    )

    dynamic_gex_by_strike["prev_abs_gex"] = (
        dynamic_gex_by_strike
        .groupby("right")["abs_gex"]
        .shift(1)
    )

    dynamic_gex_by_strike["next_abs_gex"] = (
        dynamic_gex_by_strike
        .groupby("right")["abs_gex"]
        .shift(-1)
    )

    dynamic_gex_by_strike["neighbor_gex_avg"] = (
        dynamic_gex_by_strike[
            ["prev_abs_gex", "next_abs_gex"]
        ]
        .mean(axis=1)
    )

    dynamic_gex_by_strike["neighbor_concentration"] = (
        dynamic_gex_by_strike["abs_gex"]
        / (
            dynamic_gex_by_strike["abs_gex"]
            + dynamic_gex_by_strike["neighbor_gex_avg"].fillna(0)
            + 1
        )
    )

    dynamic_gex_by_strike["max_neighbor_side"] = (
        dynamic_gex_by_strike
        .groupby("right")["neighbor_concentration"]
        .transform("max")
    )

    dynamic_gex_by_strike["neighbor_score"] = (
        dynamic_gex_by_strike["neighbor_concentration"]
        / dynamic_gex_by_strike["max_neighbor_side"].replace(0, 1)
    )

    dynamic_gex_by_strike["wall_score"] = (
        0.55 * dynamic_gex_by_strike["gex_score"]
        + 0.25 * dynamic_gex_by_strike["oi_score"]
        + 0.20 * dynamic_gex_by_strike["neighbor_score"]
    )    

    dynamic_gex_top = (
        dynamic_gex_by_strike
        .assign(
            abs_dynamic_gex=
            dynamic_gex_by_strike["dealer_dynamic_gex"].abs()
        )
        .sort_values(
            "abs_dynamic_gex",
            ascending=False
        )
        .head(10)
    )

    print(
        dynamic_gex_top[
            [
                "strike",
                "right",
                "open_interest",
                "dealer_dynamic_gex",
                "wall_score",
                "neighbor_concentration",
                "neighbor_score",
                "distance_from_spot"
            ]
        ].to_string(index=False)
    )

    calls_dynamic = dynamic_gex_by_strike[
        (dynamic_gex_by_strike["right"] == "CALL")
        & (dynamic_gex_by_strike["strike"] >= current_spot + 10)
        & (dynamic_gex_by_strike["dealer_dynamic_gex"].abs() > 0)
    ].copy()

    if not calls_dynamic.empty:
        dynamic_call_wall = calls_dynamic.loc[
            calls_dynamic[
                "wall_score"
            ].idxmax()
        ]

        current_call_wall = int(dynamic_call_wall["strike"])

        if LAST_DYNAMIC_CALL_WALL == current_call_wall:
            CALL_WALL_STREAK += 1
        else:
            LAST_DYNAMIC_CALL_WALL = current_call_wall
            CALL_WALL_STREAK = 1

        call_wall_status = (
            "CONFIRMADO"
            if CALL_WALL_STREAK >= 3
            else "PROVISIONAL"
        )

        if CALL_WALL_STREAK >= 3:
            CONFIRMED_CALL_WALL = current_call_wall

        if CONFIRMED_CALL_WALL is not None:
            if current_call_wall == CONFIRMED_CALL_WALL:
                CONFIRMED_CALL_WALL_MISSES = 0
            else:
                CONFIRMED_CALL_WALL_MISSES += 1

        if CONFIRMED_CALL_WALL_MISSES >= 3:
            print(
                f"Call Wall confirmado CADUCADO: "
                f"{CONFIRMED_CALL_WALL}"
            )

            CONFIRMED_CALL_WALL = None
            CONFIRMED_CALL_WALL_MISSES = 0

        print(
            f"Dynamic Call Wall {call_wall_status}: "
            f"{dynamic_call_wall['strike']:.0f} | "
            f"GEX ${dynamic_call_wall['dealer_dynamic_gex']:,.0f} | "
            f"OI {dynamic_call_wall['open_interest']:.0f} | "
            f"Score {dynamic_call_wall['wall_score']:.3f} | "
            f"Neighbor {dynamic_call_wall['neighbor_score']:.3f} | "
            f"Dist {dynamic_call_wall['distance_from_spot']:+.1f} | "
            f"Streak {CALL_WALL_STREAK}"
        )

    else:
        LAST_DYNAMIC_CALL_WALL = None
        CALL_WALL_STREAK = 0

        if CONFIRMED_CALL_WALL is not None:
            CONFIRMED_CALL_WALL_MISSES += 1

            if CONFIRMED_CALL_WALL_MISSES >= 3:
                print(
                    f"Call Wall confirmado CADUCADO: "
                    f"{CONFIRMED_CALL_WALL}"
                )

                CONFIRMED_CALL_WALL = None
                CONFIRMED_CALL_WALL_MISSES = 0

        print(
            "Dynamic Call Wall: SIN CANDIDATO | "
            "Streak 0"
        )

    puts_dynamic = dynamic_gex_by_strike[
        (dynamic_gex_by_strike["right"] == "PUT")
        & (dynamic_gex_by_strike["strike"] <= current_spot - 10)
        & (dynamic_gex_by_strike["dealer_dynamic_gex"].abs() > 0)
    ].copy()

    if not puts_dynamic.empty:
        dynamic_put_wall = puts_dynamic.loc[
            puts_dynamic[
                "wall_score"
            ].idxmax()
        ]

        current_put_wall = int(dynamic_put_wall["strike"])

        if LAST_DYNAMIC_PUT_WALL == current_put_wall:
            PUT_WALL_STREAK += 1
        else:
            LAST_DYNAMIC_PUT_WALL = current_put_wall
            PUT_WALL_STREAK = 1

        put_wall_status = (
            "CONFIRMADO"
            if PUT_WALL_STREAK >= 3
            else "PROVISIONAL"
        )

        if PUT_WALL_STREAK >= 3:
            CONFIRMED_PUT_WALL = current_put_wall

        if CONFIRMED_PUT_WALL is not None:
            if current_put_wall == CONFIRMED_PUT_WALL:
                CONFIRMED_PUT_WALL_MISSES = 0
            else:
                CONFIRMED_PUT_WALL_MISSES += 1

        if CONFIRMED_PUT_WALL_MISSES >= 3:
            print(
                f"Put Wall confirmado CADUCADO: "
                f"{CONFIRMED_PUT_WALL}"
            )

            CONFIRMED_PUT_WALL = None
            CONFIRMED_PUT_WALL_MISSES = 0

        print(
            f"Dynamic Put Wall {put_wall_status}: "
            f"{dynamic_put_wall['strike']:.0f} | "
            f"GEX ${dynamic_put_wall['dealer_dynamic_gex']:,.0f} | "
            f"OI {dynamic_put_wall['open_interest']:.0f} | "
            f"Score {dynamic_put_wall['wall_score']:.3f} | "
            f"Neighbor {dynamic_put_wall['neighbor_score']:.3f} | "
            f"Dist {dynamic_put_wall['distance_from_spot']:+.1f} | "
            f"Streak {PUT_WALL_STREAK}"
        )

    else:
        LAST_DYNAMIC_PUT_WALL = None
        PUT_WALL_STREAK = 0

        if CONFIRMED_PUT_WALL is not None:
            CONFIRMED_PUT_WALL_MISSES += 1

        if CONFIRMED_PUT_WALL_MISSES >= 3:
            print(
                f"Put Wall confirmado CADUCADO: "
                f"{CONFIRMED_PUT_WALL}"
            )

            CONFIRMED_PUT_WALL = None
            CONFIRMED_PUT_WALL_MISSES = 0

        print(
            "Dynamic Put Wall: SIN CANDIDATO | "
            "Streak 0"
        )

    print(
        f"Último Call Wall confirmado: "
        f"{CONFIRMED_CALL_WALL if CONFIRMED_CALL_WALL is not None else 'NINGUNO'} | "
        f"Misses {CONFIRMED_CALL_WALL_MISSES}"
    )

    print(
        f"Último Put Wall confirmado: "
        f"{CONFIRMED_PUT_WALL if CONFIRMED_PUT_WALL is not None else 'NINGUNO'} | "
        f"Misses {CONFIRMED_PUT_WALL_MISSES}"
    )

    if CONFIRMED_CALL_WALL is not None:
        CURRENT_CALL_WALL_DISTANCE = float(
            CONFIRMED_CALL_WALL
            - current_spot
        )
    else:
        CURRENT_CALL_WALL_DISTANCE = None

    if CONFIRMED_PUT_WALL is not None:
        CURRENT_PUT_WALL_DISTANCE = float(
            current_spot
            - CONFIRMED_PUT_WALL
        )
    else:
        CURRENT_PUT_WALL_DISTANCE = None

    if (
        CONFIRMED_CALL_WALL is None
        and CONFIRMED_PUT_WALL is None
    ):
        wall_location = "WALLS UNAVAILABLE"

    elif (
        CONFIRMED_CALL_WALL is not None
        and current_spot
        > CONFIRMED_CALL_WALL
        + WALL_PROXIMITY_POINTS
    ):
        wall_location = "ABOVE CALL WALL"

    elif (
        CONFIRMED_PUT_WALL is not None
        and current_spot
        < CONFIRMED_PUT_WALL
        - WALL_PROXIMITY_POINTS
    ):
        wall_location = "BELOW PUT WALL"

    elif (
        CONFIRMED_CALL_WALL is not None
        and abs(
            current_spot
            - CONFIRMED_CALL_WALL
        ) <= WALL_PROXIMITY_POINTS
    ):
        wall_location = "AT CALL WALL"

    elif (
        CONFIRMED_PUT_WALL is not None
        and abs(
            current_spot
            - CONFIRMED_PUT_WALL
        ) <= WALL_PROXIMITY_POINTS
    ):
        wall_location = "AT PUT WALL"

    elif (
        CONFIRMED_CALL_WALL is not None
        and CONFIRMED_PUT_WALL is not None
        and CONFIRMED_PUT_WALL
        < current_spot
        < CONFIRMED_CALL_WALL
    ):
        wall_location = "INSIDE WALL RANGE"

    else:
        wall_location = "TRANSITION ZONE"

    CURRENT_WALL_LOCATION = wall_location

    if wall_location == "AT CALL WALL":
        wall_context = "CALL WALL TEST"
    elif wall_location == "AT PUT WALL":
        wall_context = "PUT WALL TEST"
    elif wall_location == "ABOVE CALL WALL":
        wall_context = "CALL WALL BREAKOUT ZONE"
    elif wall_location == "BELOW PUT WALL":
        wall_context = "PUT WALL BREAKDOWN ZONE"
    elif wall_location == "INSIDE WALL RANGE":
        wall_context = "RANGE INTERIOR"
    elif wall_location == "TRANSITION ZONE":
        wall_context = "WALL TRANSITION"
    else:
        wall_context = "UNAVAILABLE"

    CURRENT_WALL_CONTEXT = wall_context

    if (
        not CURRENT_FLOW_USABLE
        or CURRENT_COMBINED_MARKET_STATE == "BLOCKED"
    ):
        full_market_context = "BLOCKED"
    else:
        full_market_context = (
            f"{CURRENT_COMBINED_MARKET_STATE} | "
            f"{CURRENT_WALL_CONTEXT}"
        )

    CURRENT_FULL_MARKET_CONTEXT = (
        full_market_context
    )

    positive_gamma_regime = gamma_regime in (
        "POSITIVE GAMMA",
        "POSITIVE GAMMA STRONG"
    )

    negative_gamma_regime = gamma_regime in (
        "NEGATIVE GAMMA",
        "NEGATIVE GAMMA STRONG"
    )

    bullish_bias = directional_bias in (
        "BULLISH",
        "BULLISH STRONG"
    )

    bearish_bias = directional_bias in (
        "BEARISH",
        "BEARISH STRONG"
    )

    strong_alignment = (
        "STRONG" in gamma_regime
        and "STRONG" in directional_bias
    )

    if CURRENT_FORCED_EXIT_REQUIRED:

        signal_candidate = "FORCED EXIT"
        signal_reason = "MANDATORY EXIT AT 15:30 ET"
        setup_quality = "MANDATORY"

    elif not CURRENT_FLOW_USABLE:

        signal_candidate = "BLOCKED"
        signal_reason = "FLOW DATA NOT USABLE"
        setup_quality = "NONE"

    elif hedge_pressure == "LOW ACTIVITY":

        signal_candidate = "WAIT"
        signal_reason = (
            f"HEDGE ACTIVITY BELOW MINIMUM "
            f"${MIN_ABS_HEDGE_NOTIONAL:,.0f}"
        )
        setup_quality = "NONE"


    elif not CURRENT_SIGNAL_PERMISSION:

        signal_candidate = "WAIT"
        signal_reason = CURRENT_OPERATIONAL_REASON
        setup_quality = "NONE"

    elif (
        wall_context == "PUT WALL TEST"
        and positive_gamma_regime
        and bullish_bias
    ):

        signal_candidate = "LONG MEAN REVERSION"
        signal_reason = (
            "BULLISH HEDGE PRESSURE AT PUT WALL "
            "IN POSITIVE GAMMA"
        )
        setup_quality = (
            "STRONG"
            if strong_alignment
            else "STANDARD"
        )

    elif (
        wall_context == "CALL WALL TEST"
        and positive_gamma_regime
        and bearish_bias
    ):

        signal_candidate = "SHORT MEAN REVERSION"
        signal_reason = (
            "BEARISH HEDGE PRESSURE AT CALL WALL "
            "IN POSITIVE GAMMA"
        )
        setup_quality = (
            "STRONG"
            if strong_alignment
            else "STANDARD"
        )

    elif (
        wall_context == "CALL WALL BREAKOUT ZONE"
        and negative_gamma_regime
        and bullish_bias
    ):

        signal_candidate = "LONG BREAKOUT"
        signal_reason = (
            "BULLISH HEDGE PRESSURE ABOVE CALL WALL "
            "IN NEGATIVE GAMMA"
        )
        setup_quality = (
            "STRONG"
            if strong_alignment
            else "STANDARD"
        )

    elif (
        wall_context == "PUT WALL BREAKDOWN ZONE"
        and negative_gamma_regime
        and bearish_bias
    ):

        signal_candidate = "SHORT BREAKDOWN"
        signal_reason = (
            "BEARISH HEDGE PRESSURE BELOW PUT WALL "
            "IN NEGATIVE GAMMA"
        )
        setup_quality = (
            "STRONG"
            if strong_alignment
            else "STANDARD"
        )

    else:

        signal_candidate = "WAIT"
        signal_reason = (
            "NO VALID WALL, GAMMA AND FLOW ALIGNMENT"
        )
        setup_quality = "NONE"

    CURRENT_SIGNAL_CANDIDATE = signal_candidate
    CURRENT_SIGNAL_REASON = signal_reason
    CURRENT_SETUP_QUALITY = setup_quality

    actionable_signal_candidates = (
        "LONG MEAN REVERSION",
        "SHORT MEAN REVERSION",
        "LONG BREAKOUT",
        "SHORT BREAKDOWN",
    )

    if signal_candidate == "FORCED EXIT":
        LAST_ACTIONABLE_SIGNAL_CANDIDATE = "NONE"
        CURRENT_SIGNAL_CANDIDATE_STREAK = 0
        CURRENT_CONFIRMED_SIGNAL = "FORCED EXIT"
        CURRENT_SIGNAL_CONFIRMED = True

    elif signal_candidate in actionable_signal_candidates:
        if (
            signal_candidate
            == LAST_ACTIONABLE_SIGNAL_CANDIDATE
        ):
            CURRENT_SIGNAL_CANDIDATE_STREAK += 1
        else:
            LAST_ACTIONABLE_SIGNAL_CANDIDATE = (
                signal_candidate
            )
            CURRENT_SIGNAL_CANDIDATE_STREAK = 1

        CURRENT_SIGNAL_CONFIRMED = (
            CURRENT_SIGNAL_CANDIDATE_STREAK
            >= SIGNAL_CONFIRMATION_CYCLES
        )

        CURRENT_CONFIRMED_SIGNAL = (
            signal_candidate
            if CURRENT_SIGNAL_CONFIRMED
            else "NONE"
        )

    else:
        LAST_ACTIONABLE_SIGNAL_CANDIDATE = "NONE"
        CURRENT_SIGNAL_CANDIDATE_STREAK = 0
        CURRENT_CONFIRMED_SIGNAL = "NONE"
        CURRENT_SIGNAL_CONFIRMED = False

    CURRENT_ENTRY_EXECUTION_PERMISSION = (
        CURRENT_SIGNAL_CONFIRMED
        and CURRENT_CONFIRMED_SIGNAL
        in actionable_signal_candidates
        and CURRENT_SIGNAL_PERMISSION
        and CURRENT_RISK_PERMISSION
        and not CURRENT_FORCED_EXIT_REQUIRED
        and CURRENT_TRADING_STATUS == "ACTIVE"
    )

    CURRENT_EXIT_EXECUTION_PERMISSION = (
        CURRENT_SIGNAL_CONFIRMED
        and CURRENT_CONFIRMED_SIGNAL == "FORCED EXIT"
        and CURRENT_FORCED_EXIT_REQUIRED
        and CURRENT_TRADING_STATUS == "FORCED EXIT"
    )

    if EXECUTION_MODE == "LIVE":

        refresh_broker_reconciliation()

        if not CURRENT_POSITION_RECONCILIATION_OK:
            CURRENT_ENTRY_EXECUTION_PERMISSION = False
            CURRENT_EXIT_EXECUTION_PERMISSION = False

    build_execution_intent()

    CURRENT_EXECUTION_SAFETY_OK, CURRENT_EXECUTION_SAFETY_REASON = (
        execution_safety_check()
    )

    dispatch_result = dispatch_execution()

    CURRENT_POSITION_VALID, CURRENT_POSITION_VALIDATION_REASON = (
        validate_position_state()
    )

    CURRENT_DISPATCH_STATUS = dispatch_result.get(
        "status",
        "UNKNOWN"
    )

    CURRENT_DISPATCH_REASON = dispatch_result.get(
        "reason",
        "NO DISPATCH REASON"
    )

    if CURRENT_DISPATCH_STATUS == "IDLE":
        CURRENT_DISPATCH_ID = None
    else:
        CURRENT_DISPATCH_ID = uuid.uuid4().hex

    broker_response = dispatch_result.get(
        "broker_response"
    )

    if CURRENT_DISPATCH_STATUS == "SUBMITTED":

        CURRENT_BROKER_ORDER_ID = None
        CURRENT_BROKER_ORDER_STATUS = "SUBMITTED"
        CURRENT_BROKER_ORDER_STATE = "OPEN"
        CURRENT_BROKER_ORDER_STATUS_DESCRIPTION = "PENDING BROKER STATUS"

        if isinstance(broker_response, dict):

            orders = broker_response.get("Orders")

            if isinstance(orders, list) and orders:

                first_order = orders[0]

                if isinstance(first_order, dict):

                    CURRENT_BROKER_ORDER_ID = (
                        first_order.get("OrderID")
                    )

                    CURRENT_BROKER_ORDER_STATUS = (
                        first_order.get(
                            "Status",
                            first_order.get(
                                "OrderStatus",
                                "SUBMITTED"
                            )
                        )
                    )

            else:

                CURRENT_BROKER_ORDER_ID = (
                    broker_response.get("OrderID")
                )

                CURRENT_BROKER_ORDER_STATUS = (
                    broker_response.get(
                        "Status",
                        broker_response.get(
                            "OrderStatus",
                            "SUBMITTED"
                        )
                    )
                )

    elif (
        CURRENT_DISPATCH_STATUS == "SUBMIT_FAILED"
        and str(CURRENT_DISPATCH_REASON).startswith(
            "ORDER SUBMISSION STATUS UNKNOWN:"
        )
    ):
        CURRENT_BROKER_ORDER_ID = None
        CURRENT_BROKER_ORDER_STATUS = "UNKNOWN"
        CURRENT_BROKER_ORDER_STATUS_DESCRIPTION = (
            CURRENT_DISPATCH_REASON
        )
        CURRENT_BROKER_ORDER_STATE = "UNKNOWN"

    if (
        EXECUTION_MODE == "LIVE"
        and CURRENT_BROKER_ACCOUNT_ID
        and CURRENT_BROKER_ORDER_STATE in (
            "OPEN",
            "UNKNOWN",
        )
        and not CURRENT_BROKER_ORDER_ID
    ):
        pending_order = {
            "symbol": CURRENT_PENDING_ORDER_SYMBOL,
            "side": CURRENT_PENDING_ORDER_SIDE,
            "quantity": CURRENT_PENDING_ORDER_QUANTITY,
            "submitted_at": CURRENT_PENDING_ORDER_SUBMITTED_AT,
        }

        reconciliation = reconcile_pending_order(
            CURRENT_BROKER_ACCOUNT_ID,
            pending_order
        )

        if (
            reconciliation.get("ok")
            and reconciliation.get("status") == "SINGLE_MATCH"
            and reconciliation.get("match_count") == 1
        ):
            matched_order = reconciliation["matches"][0]

            CURRENT_BROKER_ORDER_ID = matched_order.get(
                "OrderID"
            )

            CURRENT_BROKER_ORDER_STATUS = matched_order.get(
                "Status",
                CURRENT_BROKER_ORDER_STATUS
            )

            CURRENT_BROKER_ORDER_STATUS_DESCRIPTION = (
                matched_order.get(
                    "StatusDescription",
                    CURRENT_BROKER_ORDER_STATUS_DESCRIPTION
                )
            )

            CURRENT_BROKER_ORDER_STATE = (
                classify_tradestation_order_status(
                    CURRENT_BROKER_ORDER_STATUS,
                    CURRENT_BROKER_ORDER_STATUS_DESCRIPTION
                )
            )

    if (
        EXECUTION_MODE == "LIVE"
        and CURRENT_BROKER_ACCOUNT_ID
        and CURRENT_BROKER_ORDER_ID
    ):
        order_lookup = get_tradestation_order_by_id(
            CURRENT_BROKER_ACCOUNT_ID,
            CURRENT_BROKER_ORDER_ID
        )

        if order_lookup.get("ok"):

            broker_order = order_lookup.get(
                "order"
            )

            if isinstance(broker_order, dict):

                CURRENT_BROKER_ORDER_STATUS = (
                    broker_order.get(
                        "Status",
                        CURRENT_BROKER_ORDER_STATUS
                    )
                )

                CURRENT_BROKER_ORDER_STATUS_DESCRIPTION = (
                    broker_order.get(
                        "StatusDescription",
                        CURRENT_BROKER_ORDER_STATUS_DESCRIPTION
                    )
                )

                CURRENT_BROKER_ORDER_STATE = (
                    classify_tradestation_order_status(
                        CURRENT_BROKER_ORDER_STATUS,
                        CURRENT_BROKER_ORDER_STATUS_DESCRIPTION
                    )
                )

    call_wall_distance_text = (
        f"{CURRENT_CALL_WALL_DISTANCE:+.1f}"
        if CURRENT_CALL_WALL_DISTANCE is not None
        else "N/A"
    )

    put_wall_distance_text = (
        f"{CURRENT_PUT_WALL_DISTANCE:+.1f}"
        if CURRENT_PUT_WALL_DISTANCE is not None
        else "N/A"
    )

    print(
        f"Wall Location: "
        f"{CURRENT_WALL_LOCATION}"
    )

    print(
        f"Distance to Call Wall: "
        f"{call_wall_distance_text} pts"
    )

    print(
        f"Distance from Put Wall: "
        f"{put_wall_distance_text} pts"
    )

    print(
        f"Wall Context: "
        f"{CURRENT_WALL_CONTEXT}"
    )

    print(
        f"Full Market Context: "
        f"{CURRENT_FULL_MARKET_CONTEXT}"
    )

    print(
        f"Signal Candidate: "
        f"{CURRENT_SIGNAL_CANDIDATE}"
    )

    print(
        f"Setup Quality: "
        f"{CURRENT_SETUP_QUALITY}"
    )

    print(
        f"Signal Reason: "
        f"{CURRENT_SIGNAL_REASON}"
    )

    print(
        f"Candidate Streak: "
        f"{CURRENT_SIGNAL_CANDIDATE_STREAK}/"
        f"{SIGNAL_CONFIRMATION_CYCLES}"
    )

    print(
        f"Signal Confirmed: "
        f"{CURRENT_SIGNAL_CONFIRMED}"
    )

    print(
        f"Confirmed Signal: "
        f"{CURRENT_CONFIRMED_SIGNAL}"
    )

    print(
        f"Risk Status: {CURRENT_RISK_STATUS} | "
        f"Permission: {CURRENT_RISK_PERMISSION}"
    )

    print(
        f"Risk Reason: {CURRENT_RISK_REASON}"
    )

    print(
        f"Entry Execution Permission: "
        f"{CURRENT_ENTRY_EXECUTION_PERMISSION}"
    )

    print(
        f"Exit Execution Permission: "
        f"{CURRENT_EXIT_EXECUTION_PERMISSION}"
    )

    print(
        f"Execution Mode: {EXECUTION_MODE} | "
        f"Live Enabled: {LIVE_ORDER_EXECUTION_ENABLED}"
    )
    
    print(
        f"Execution Status: {CURRENT_EXECUTION_STATUS} | "
        f"Action: {CURRENT_EXECUTION_ACTION} | "
        f"Side: {CURRENT_EXECUTION_SIDE} | "
        f"Qty: {CURRENT_EXECUTION_QUANTITY} | "
        f"Type: {CURRENT_EXECUTION_ORDER_TYPE}"
    )
    
    print(
        f"Execution Reason: {CURRENT_EXECUTION_REASON}"
    )

    print(
        f"Execution Safety: {CURRENT_EXECUTION_SAFETY_OK} | "
        f"Reason: {CURRENT_EXECUTION_SAFETY_REASON}"
    )

    print(
        f"Dispatch Status: {CURRENT_DISPATCH_STATUS} | "
        f"Reason: {CURRENT_DISPATCH_REASON}"
    )

    print(
        f"Dispatch ID: {CURRENT_DISPATCH_ID}"
    )

    print(
        f"Position State: {CURRENT_POSITION_STATE} | "
        f"Contracts: {CURRENT_POSITION_CONTRACTS} | "
        f"Entry Side: {CURRENT_POSITION_ENTRY_SIDE}"
    )

    print(
        f"Position Valid: {CURRENT_POSITION_VALID} | "
        f"Reason: {CURRENT_POSITION_VALIDATION_REASON}"
    )

    if not calls_dynamic.empty:
        dominant_call = calls_dynamic.loc[
            calls_dynamic["dealer_dynamic_gex"].abs().idxmax()
        ]

        print(
            f"\nCALL dominante: "
            f"{dominant_call['strike']:.0f} | "
            f"GEX ${dominant_call['dealer_dynamic_gex']:,.0f}"
        )

    if not puts_dynamic.empty:
        dominant_put = puts_dynamic.loc[
            puts_dynamic["dealer_dynamic_gex"].abs().idxmax()
        ]

        print(
            f"PUT dominante: "
            f"{dominant_put['strike']:.0f} | "
            f"GEX ${dominant_put['dealer_dynamic_gex']:,.0f}"
        )
    
    print(
        "\nPresiona CTRL+C para detener."
    )


# ============================================================
# GUARDAR SNAPSHOT EN CSV
# ============================================================

def save_live_json(df, now_et, spx_spot):

    live_df = df.copy()

    live_df["snapshot_time"] = (
        now_et.isoformat()
    )

    records = live_df.to_dict(
        orient="records"
    )

    import json

    live_payload = {
        "snapshot_time": now_et.isoformat(),
        "symbol": SYMBOL,
        "expiration": now_et.date().isoformat(),
        "spx_spot": spx_spot,
        "contracts": len(live_df),

        "confirmed_call_wall": CONFIRMED_CALL_WALL,
        "confirmed_put_wall": CONFIRMED_PUT_WALL,
        "call_wall_misses": CONFIRMED_CALL_WALL_MISSES,
        "put_wall_misses": CONFIRMED_PUT_WALL_MISSES,
        "call_wall_distance_points": CURRENT_CALL_WALL_DISTANCE,
        "put_wall_distance_points": CURRENT_PUT_WALL_DISTANCE,
        "wall_location": CURRENT_WALL_LOCATION,
        "wall_context": CURRENT_WALL_CONTEXT,
        "full_market_context": CURRENT_FULL_MARKET_CONTEXT,

        "signal_candidate": CURRENT_SIGNAL_CANDIDATE,
        "setup_quality": CURRENT_SETUP_QUALITY,
        "signal_reason": CURRENT_SIGNAL_REASON,
        "signal_confirmation_cycles": SIGNAL_CONFIRMATION_CYCLES,
        "signal_candidate_streak": CURRENT_SIGNAL_CANDIDATE_STREAK,

        "signal_confirmed": CURRENT_SIGNAL_CONFIRMED,
        "confirmed_signal": CURRENT_CONFIRMED_SIGNAL,

        "risk_status": CURRENT_RISK_STATUS,
        "risk_permission": CURRENT_RISK_PERMISSION,
        "risk_reason": CURRENT_RISK_REASON,
        "position_size_contracts": CURRENT_POSITION_SIZE_CONTRACTS,
        "stop_loss_points": CURRENT_STOP_LOSS_POINTS,
        "take_profit_points": CURRENT_TAKE_PROFIT_POINTS,
        "max_loss_usd": CURRENT_MAX_LOSS_USD,
        "entry_execution_permission": CURRENT_ENTRY_EXECUTION_PERMISSION,
        "exit_execution_permission": CURRENT_EXIT_EXECUTION_PERMISSION,
        "execution_mode": EXECUTION_MODE,
        "live_order_execution_enabled": LIVE_ORDER_EXECUTION_ENABLED,
        "order_execution_environment": ORDER_EXECUTION_ENVIRONMENT,
        "execution_status": CURRENT_EXECUTION_STATUS,
        "execution_action": CURRENT_EXECUTION_ACTION,
        "execution_reason": CURRENT_EXECUTION_REASON,
        "execution_symbol": CURRENT_EXECUTION_SYMBOL,
        "execution_side": CURRENT_EXECUTION_SIDE,
        "execution_quantity": CURRENT_EXECUTION_QUANTITY,
        "execution_order_type": CURRENT_EXECUTION_ORDER_TYPE,
        "execution_safety_ok": CURRENT_EXECUTION_SAFETY_OK,
        "execution_safety_reason": CURRENT_EXECUTION_SAFETY_REASON,
        "dispatch_status": CURRENT_DISPATCH_STATUS,
        "dispatch_reason": CURRENT_DISPATCH_REASON,
        "dispatch_id": CURRENT_DISPATCH_ID,
        "broker_order_id": CURRENT_BROKER_ORDER_ID,
        "broker_order_status": CURRENT_BROKER_ORDER_STATUS,
        "broker_order_status_description": CURRENT_BROKER_ORDER_STATUS_DESCRIPTION,
        "broker_order_state": CURRENT_BROKER_ORDER_STATE,
        "pending_order_action": CURRENT_PENDING_ORDER_ACTION,
        "pending_order_side": CURRENT_PENDING_ORDER_SIDE,
        "pending_order_quantity": CURRENT_PENDING_ORDER_QUANTITY,
        "pending_order_symbol": CURRENT_PENDING_ORDER_SYMBOL,
        "pending_order_submitted_at": CURRENT_PENDING_ORDER_SUBMITTED_AT,
        "position_state": CURRENT_POSITION_STATE,
        "position_contracts": CURRENT_POSITION_CONTRACTS,
        "position_entry_side": CURRENT_POSITION_ENTRY_SIDE,
        "position_valid": CURRENT_POSITION_VALID,
        "position_validation_reason": CURRENT_POSITION_VALIDATION_REASON,
        "broker_account_id": CURRENT_BROKER_ACCOUNT_ID,
        "broker_position_available": CURRENT_BROKER_POSITION_AVAILABLE,
        "broker_position_reason": CURRENT_BROKER_POSITION_REASON,
        "position_reconciliation_ok": CURRENT_POSITION_RECONCILIATION_OK,
        "position_reconciliation_action": CURRENT_POSITION_RECONCILIATION_ACTION,
        "position_reconciliation_reason": CURRENT_POSITION_RECONCILIATION_REASON,


        "gamma_balance": CURRENT_GAMMA_BALANCE,
        "gamma_regime": CURRENT_GAMMA_REGIME,
        "net_dynamic_gex": CURRENT_NET_DYNAMIC_GEX,
        "positive_dynamic_gex": CURRENT_POSITIVE_DYNAMIC_GEX,
        "negative_dynamic_gex": CURRENT_NEGATIVE_DYNAMIC_GEX,
        "dealer_flow_gex_total": CURRENT_DEALER_FLOW_GEX,
        "dealer_dynamic_gex_total": CURRENT_DEALER_DYNAMIC_GEX,
        "dealer_delta_notional": CURRENT_DEALER_DELTA_NOTIONAL,
        "dealer_hedge_notional": CURRENT_DEALER_HEDGE_NOTIONAL,
        "absolute_hedge_notional": CURRENT_ABS_HEDGE_NOTIONAL,
        "minimum_abs_hedge_notional": MIN_ABS_HEDGE_NOTIONAL,
        "hedge_pressure_balance": CURRENT_HEDGE_PRESSURE_BALANCE,
        "hedge_pressure": CURRENT_HEDGE_PRESSURE,
        "directional_bias": CURRENT_DIRECTIONAL_BIAS,
        "combined_market_state": CURRENT_COMBINED_MARKET_STATE,

        "fresh_trades": CURRENT_FRESH_TRADES,
        "new_trades": CURRENT_NEW_TRADES,
        "rejected_trades": CURRENT_REJECTED_TRADES,
        "new_trade_age_min_sec": CURRENT_NEW_TRADE_AGE_MIN_SEC,
        "new_trade_age_max_sec": CURRENT_NEW_TRADE_AGE_MAX_SEC,
        "trade_max_age_seconds": TRADE_MAX_AGE_SECONDS,
        "trade_future_tolerance_seconds": TRADE_FUTURE_TOLERANCE_SECONDS,
        "temporal_acceptance_ratio": CURRENT_TEMPORAL_ACCEPTANCE_RATIO,
        "temporal_quality": CURRENT_TEMPORAL_QUALITY,
        "flow_data_status": CURRENT_FLOW_DATA_STATUS,
        "flow_usable": CURRENT_FLOW_USABLE,

        "forced_exit_required": CURRENT_FORCED_EXIT_REQUIRED,
        "trading_status": CURRENT_TRADING_STATUS,
        "forced_exit_time_et": "15:30",

        "operational_mode": CURRENT_OPERATIONAL_MODE,
        "signal_permission": CURRENT_SIGNAL_PERMISSION,
        "operational_reason": CURRENT_OPERATIONAL_REASON,

        "last_fresh_trade_cycle_time": LAST_FRESH_TRADE_CYCLE_TIME,
        "fresh_trade_age_sec": CURRENT_FRESH_TRADE_AGE_SEC,
        "flow_freshness": CURRENT_FLOW_FRESHNESS,

        "dealer_sell_options_count": CURRENT_DEALER_SELL_OPTIONS,
        "dealer_buy_options_count": CURRENT_DEALER_BUY_OPTIONS,
        "neutral_trades": CURRENT_NEUTRAL_TRADES,
        "classified_trade_ratio": CURRENT_CLASSIFIED_TRADE_RATIO,
        "neutral_trade_ratio": CURRENT_NEUTRAL_TRADE_RATIO,

        "data": records
    }

    temp_live_output_json = LIVE_OUTPUT_JSON + ".tmp"

    with open(
        temp_live_output_json,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            live_payload,
            f,
            ensure_ascii=False,
            indent=2,
            default=str
        )

    os.replace(
        temp_live_output_json,
        LIVE_OUTPUT_JSON
    )

def save_signal_history(now_et, spx_spot):

    if not is_signal_history_window(now_et):
        return

    os.makedirs(
        SIGNAL_HISTORY_FOLDER,
        exist_ok=True
    )

    daily_filename = (
        f"SPX_SIGNALS_{now_et.strftime('%Y-%m-%d')}.csv"
    )

    daily_path = os.path.join(
        SIGNAL_HISTORY_FOLDER,
        daily_filename
    )

    signal_row = {
        "snapshot_time": now_et.isoformat(),
        "spx_spot": spx_spot,

        "flow_data_status": CURRENT_FLOW_DATA_STATUS,
        "flow_usable": CURRENT_FLOW_USABLE,
        "fresh_trades": CURRENT_FRESH_TRADES,
        "new_trades": CURRENT_NEW_TRADES,
        "rejected_trades": CURRENT_REJECTED_TRADES,
        "temporal_acceptance_ratio": CURRENT_TEMPORAL_ACCEPTANCE_RATIO,

        "dealer_delta_notional": CURRENT_DEALER_DELTA_NOTIONAL,
        "dealer_hedge_notional": CURRENT_DEALER_HEDGE_NOTIONAL,
        "absolute_hedge_notional": CURRENT_ABS_HEDGE_NOTIONAL,
        "minimum_abs_hedge_notional": MIN_ABS_HEDGE_NOTIONAL,
        "hedge_pressure_balance": CURRENT_HEDGE_PRESSURE_BALANCE,
        "hedge_pressure": CURRENT_HEDGE_PRESSURE,

        "gamma_balance": CURRENT_GAMMA_BALANCE,
        "gamma_regime": CURRENT_GAMMA_REGIME,
        "net_dynamic_gex": CURRENT_NET_DYNAMIC_GEX,
        "directional_bias": CURRENT_DIRECTIONAL_BIAS,
        "operational_mode": CURRENT_OPERATIONAL_MODE,
        "operational_reason": CURRENT_OPERATIONAL_REASON,
        "combined_market_state": CURRENT_COMBINED_MARKET_STATE,

        "confirmed_call_wall": CONFIRMED_CALL_WALL,
        "confirmed_put_wall": CONFIRMED_PUT_WALL,
        "call_wall_distance_points": CURRENT_CALL_WALL_DISTANCE,
        "put_wall_distance_points": CURRENT_PUT_WALL_DISTANCE,
        "wall_location": CURRENT_WALL_LOCATION,
        "wall_context": CURRENT_WALL_CONTEXT,
        "full_market_context": CURRENT_FULL_MARKET_CONTEXT,

        "signal_candidate": CURRENT_SIGNAL_CANDIDATE,
        "setup_quality": CURRENT_SETUP_QUALITY,
        "signal_reason": CURRENT_SIGNAL_REASON,
        "signal_confirmation_cycles": SIGNAL_CONFIRMATION_CYCLES,
        "signal_candidate_streak": CURRENT_SIGNAL_CANDIDATE_STREAK,

        "signal_confirmed": CURRENT_SIGNAL_CONFIRMED,
        "confirmed_signal": CURRENT_CONFIRMED_SIGNAL,

        "risk_status": CURRENT_RISK_STATUS,
        "risk_permission": CURRENT_RISK_PERMISSION,
        "risk_reason": CURRENT_RISK_REASON,
        "position_size_contracts": CURRENT_POSITION_SIZE_CONTRACTS,
        "stop_loss_points": CURRENT_STOP_LOSS_POINTS,
        "take_profit_points": CURRENT_TAKE_PROFIT_POINTS,
        "max_loss_usd": CURRENT_MAX_LOSS_USD,
        "entry_execution_permission": CURRENT_ENTRY_EXECUTION_PERMISSION,
        "exit_execution_permission": CURRENT_EXIT_EXECUTION_PERMISSION,
        "execution_mode": EXECUTION_MODE,
        "live_order_execution_enabled": LIVE_ORDER_EXECUTION_ENABLED,
        "order_execution_environment": ORDER_EXECUTION_ENVIRONMENT,
        "execution_status": CURRENT_EXECUTION_STATUS,
        "execution_action": CURRENT_EXECUTION_ACTION,
        "execution_reason": CURRENT_EXECUTION_REASON,
        "execution_symbol": CURRENT_EXECUTION_SYMBOL,
        "execution_side": CURRENT_EXECUTION_SIDE,
        "execution_quantity": CURRENT_EXECUTION_QUANTITY,
        "execution_order_type": CURRENT_EXECUTION_ORDER_TYPE,
        "execution_safety_ok": CURRENT_EXECUTION_SAFETY_OK,
        "execution_safety_reason": CURRENT_EXECUTION_SAFETY_REASON,
        "dispatch_status": CURRENT_DISPATCH_STATUS,
        "dispatch_reason": CURRENT_DISPATCH_REASON,
        "dispatch_id": CURRENT_DISPATCH_ID,
        "broker_order_id": CURRENT_BROKER_ORDER_ID,
        "broker_order_status": CURRENT_BROKER_ORDER_STATUS,
        "broker_order_status_description": CURRENT_BROKER_ORDER_STATUS_DESCRIPTION,
        "broker_order_state": CURRENT_BROKER_ORDER_STATE,
        "pending_order_action": CURRENT_PENDING_ORDER_ACTION,
        "pending_order_side": CURRENT_PENDING_ORDER_SIDE,
        "pending_order_quantity": CURRENT_PENDING_ORDER_QUANTITY,
        "pending_order_symbol": CURRENT_PENDING_ORDER_SYMBOL,
        "pending_order_submitted_at": CURRENT_PENDING_ORDER_SUBMITTED_AT,
        "position_state": CURRENT_POSITION_STATE,
        "position_contracts": CURRENT_POSITION_CONTRACTS,
        "position_entry_side": CURRENT_POSITION_ENTRY_SIDE,
        "position_valid": CURRENT_POSITION_VALID,
        "position_validation_reason": CURRENT_POSITION_VALIDATION_REASON,
        "broker_account_id": CURRENT_BROKER_ACCOUNT_ID,
        "broker_position_available": CURRENT_BROKER_POSITION_AVAILABLE,
        "broker_position_reason": CURRENT_BROKER_POSITION_REASON,
        "position_reconciliation_ok": CURRENT_POSITION_RECONCILIATION_OK,
        "position_reconciliation_action": CURRENT_POSITION_RECONCILIATION_ACTION,
        "position_reconciliation_reason": CURRENT_POSITION_RECONCILIATION_REASON,

        "signal_permission": CURRENT_SIGNAL_PERMISSION,
        "forced_exit_required": CURRENT_FORCED_EXIT_REQUIRED,
        "trading_status": CURRENT_TRADING_STATUS,
        "forced_exit_time_et": "15:30",
    }

    file_exists = os.path.exists(
        daily_path
    )

    pd.DataFrame(
        [signal_row]
    ).to_csv(
        daily_path,
        mode="a",
        header=not file_exists,
        index=False
    )



def save_snapshot(df, now_et):

    # Solo guardar entre 9:30 y 11:30 hora de Nueva York
    if not is_history_window(now_et):
        return

    # Crear carpeta historica si no existe
    os.makedirs(
        HISTORY_FOLDER,
        exist_ok=True
    )

    # Nombre diario del archivo
    daily_filename = (
        f"SPX_0DTE_{now_et.strftime('%Y-%m-%d')}.csv"
    )

    daily_path = os.path.join(
        HISTORY_FOLDER,
        daily_filename
    )

    df_to_save = df.copy()

    # Hora exacta del snapshot
    df_to_save["snapshot_time"] = (
        now_et.isoformat()
    )

    # Comprobar si el archivo ya existe
    file_exists = os.path.exists(
        daily_path
    )

    # Guardar o agregar filas
    df_to_save.to_csv(
        daily_path,
        mode="a",
        header=not file_exists,
        index=False
    )

# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    global OPEN_INTEREST_CACHE

    # --------------------------------------------------------
    # CREAR UN SOLO CLIENTE THETADATA
    # --------------------------------------------------------

    client = create_client()

    if client is None:
        return

    # --------------------------------------------------------
    # CARGAR OPEN INTEREST UNA SOLA VEZ AL INICIAR EL DIA
    # --------------------------------------------------------

    now_et = datetime.now(MARKET_TZ)
    expiration = now_et.date()

    print(
        f"Cargando Open Interest SPXW 0DTE "
        f"para {expiration}..."
    )

    try:
        OPEN_INTEREST_CACHE = client.option_snapshot_open_interest(
            symbol=SYMBOL,
            expiration=expiration,
            strike="*",
            right="both",
            strike_range=OI_STRIKE_RANGE
        )

    except KeyboardInterrupt:
        print(
            "\nPrograma detenido por el usuario "
            "durante la carga inicial de Open Interest."
        )
        return    

    except NoDataFoundError:
        print(
            f"No hay datos SPXW 0DTE disponibles "
            f"para {expiration}."
        )
        print(
            "El programa finaliza sin iniciar el ciclo intradia."
        )
        return

    OPEN_INTEREST_CACHE = OPEN_INTEREST_CACHE[
        [
            "symbol",
            "expiration",
            "strike",
            "right",
            "open_interest"
        ]
    ].copy()

    print(
        f"Open Interest cargado: "
        f"{len(OPEN_INTEREST_CACHE)} contratos."
    )

    while True:

        try:

            # ------------------------------------------------
            # CREAR CLIENTE SI NO EXISTE
            # ------------------------------------------------

            if client is None:

                client = create_client()

            if client is None:
                return

            # ------------------------------------------------
            # OBTENER DATOS
            # ------------------------------------------------

            df, now_et = get_live_snapshot(
                client
            )

            spx_spot = get_spx_spot()

            # ------------------------------------------------
            # MOSTRAR
            # ------------------------------------------------

            display_snapshot(
                df,
                now_et
            )

            print(
                f"SPX Spot TradeStation: {spx_spot:.2f}"
            )

            save_live_json(
                df,
                now_et,
                spx_spot
            )

            save_state()

            # ------------------------------------------------
            # GUARDAR
            # ------------------------------------------------

            save_snapshot(
                df,
                now_et
            )

            save_signal_history(
                now_et,
                spx_spot
            )

            # ------------------------------------------------
            # ESPERAR
            # ------------------------------------------------

            time.sleep(
                REFRESH_SECONDS
            )

        # ====================================================
        # CTRL+C
        # ====================================================

        except KeyboardInterrupt:

            print(
                "\n\nPrograma detenido "
                "por el usuario."
            )

            break

        # ====================================================
        # ERRORES
        # ====================================================

        except Exception as e:

            error_text = str(e)

            print("\n")
            print("=" * 80)
            print("ERROR THETADATA")
            print("=" * 80)

            print(
                error_text
            )

            __import__("traceback").print_exc()

            # ------------------------------------------------
            # SESION INVALIDA
            # ------------------------------------------------

            if (
                "UNAUTHENTICATED" in error_text
                or
                "Invalid session ID" in error_text
            ):

                print(
                    "\nSesion ThetaData invalida."
                )

                print(
                    "Se eliminara el cliente actual "
                    "y se intentara crear uno nuevo."
                )

                client = None

                time.sleep(5)

            else:

                print(
                    f"\nReintentando en "
                    f"{REFRESH_SECONDS} segundos..."
                )

                time.sleep(
                    REFRESH_SECONDS
                )


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":
    load_state()
    main()