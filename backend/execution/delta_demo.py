import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass

import requests

TESTNET_BASE_URL = "https://cdn-ind.testnet.deltaex.org"

SYMBOL_MAP = {
    "BTCUSDT": "BTCUSD",
    "ETHUSDT": "ETHUSD",
}


@dataclass(frozen=True)
class DeltaProduct:
    symbol: str
    product_id: int
    contract_value: float
    tick_size: float


class DeltaDemoClient:
    """Small, testnet-only Delta Exchange execution client.

    This client refuses non-testnet base URLs so production credentials/endpoints
    cannot be accidentally used by this demo executor.
    """

    def __init__(self):
        self.enabled = os.getenv("DELTA_DEMO_ENABLED", "false").lower() == "true"
        self.api_key = os.getenv("DELTA_DEMO_API_KEY", "").strip()
        self.api_secret = os.getenv("DELTA_DEMO_API_SECRET", "").strip()
        self.base_url = TESTNET_BASE_URL
        self.timeout = (3, 15)
        self.products: dict[str, DeltaProduct] = {}

        if self.enabled and (not self.api_key or not self.api_secret):
            raise RuntimeError("DELTA_DEMO_ENABLED=true requires DELTA_DEMO_API_KEY and DELTA_DEMO_API_SECRET")

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.api_key and self.api_secret)

    def _signature(self, method: str, path: str, query_string: str, body: str, timestamp: str) -> str:
        message = method + timestamp + path + query_string + body
        return hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(self, method: str, path: str, *, params=None, payload=None, auth=False):
        body = "" if payload is None else json.dumps(payload, separators=(",", ":"))
        query_string = ""
        if params:
            # requests uses the same insertion order for params; build the signed
            # query string explicitly so the bytes signed match the request.
            from urllib.parse import urlencode
            query_string = "?" + urlencode(params)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "golden-setup-demo-bot/1.0",
        }
        if auth:
            timestamp = str(int(time.time()))
            headers.update({
                "api-key": self.api_key,
                "timestamp": timestamp,
                "signature": self._signature(method, path, query_string, body, timestamp),
            })

        response = requests.request(
            method,
            self.base_url + path,
            params=params or {},
            data=body,
            headers=headers,
            timeout=self.timeout,
        )
        try:
            data = response.json()
        except ValueError:
            data = {"success": False, "error": {"code": "invalid_json", "message": response.text[:500]}}
        if not response.ok or data.get("success") is False:
            raise RuntimeError(f"Delta API {response.status_code}: {data}")
        return data

    def load_products(self):
        for internal, exchange in SYMBOL_MAP.items():
            data = self._request("GET", f"/v2/products/{exchange}")
            p = data["result"]
            self.products[internal] = DeltaProduct(
                symbol=exchange,
                product_id=int(p["id"] if "id" in p else p["product_id"]),
                contract_value=float(p["contract_value"]),
                tick_size=float(p.get("tick_size", 0.5)),
            )
        return self.products

    def ensure_products(self):
        if not self.products:
            self.load_products()

    def contracts_for_coin_qty(self, internal_symbol: str, coin_qty: float) -> int:
        self.ensure_products()
        p = self.products[internal_symbol]
        if p.contract_value <= 0:
            raise RuntimeError(f"Invalid contract_value for {p.symbol}")
        # Delta order size is integer contracts. Never exceed the requested
        # coin quantity because that could unintentionally increase exposure.
        import math
        return max(0, int(math.floor((coin_qty / p.contract_value) + 1e-12)))

    def contracts_for_notional(self, internal_symbol: str, entry_price: float, notional: float) -> int:
        self.ensure_products()
        p = self.products[internal_symbol]
        import math
        per_contract_notional = entry_price * p.contract_value
        if per_contract_notional <= 0:
            raise RuntimeError("Invalid contract notional")
        return max(0, int(math.floor(notional / per_contract_notional + 1e-12)))

    def place_market(self, internal_symbol: str, side: str, contracts: int, *, reduce_only: bool, tag: str):
        self.ensure_products()
        if contracts <= 0:
            raise RuntimeError(f"Refusing zero-size Delta order for {internal_symbol}")
        p = self.products[internal_symbol]
        payload = {
            "product_id": p.product_id,
            "size": int(contracts),
            "side": "buy" if side == "LONG" else "sell",
            "order_type": "market_order",
            "reduce_only": bool(reduce_only),
            "client_order_id": f"golden-{tag}-{uuid.uuid4().hex[:20]}",
        }
        return self._request("POST", "/v2/orders", payload=payload, auth=True)

    def account_smoke_test(self):
        # Read-only authenticated call. Useful before enabling order execution.
        data = self._request("GET", "/v2/orders", params={"page_size": 1}, auth=True)
        return data
