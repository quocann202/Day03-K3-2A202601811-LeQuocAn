"""Deterministic e-commerce tools used by the Lab 3 ReAct agent.

These tools simulate an external commerce service.  Keeping them deterministic
makes failures reproducible in the trace and lets the lab focus on reasoning.
"""

from __future__ import annotations

from typing import Any, Callable


CATALOG = {
    "iphone": {"stock": 10, "unit_price_vnd": 25_000_000, "weight_kg": 0.4},
    "airpods": {"stock": 4, "unit_price_vnd": 4_500_000, "weight_kg": 0.1},
    "macbook air": {"stock": 0, "unit_price_vnd": 28_000_000, "weight_kg": 1.24},
}
COUPONS = {"WINNER": 10, "STUDENT": 5, "FREESHIP": 0}
DESTINATION_RATES = {"hanoi": 30_000, "ho chi minh city": 35_000, "danang": 40_000}


def _normalise_item(item_name: str) -> str:
    item = item_name.strip().lower()
    if "iphone" in item:
        return "iphone"
    if "airpod" in item:
        return "airpods"
    if "macbook" in item:
        return "macbook air"
    return item


def check_stock(item_name: str) -> dict[str, Any]:
    """Return stock plus price and weight needed for a purchase calculation."""
    item = _normalise_item(item_name)
    product = CATALOG.get(item)
    if product is None:
        return {"ok": False, "error": f"Product '{item_name}' was not found."}
    return {"ok": True, "item": item, **product}


def get_discount(coupon_code: str) -> dict[str, Any]:
    """Return a percentage discount for a valid coupon; never invent one."""
    code = coupon_code.strip().upper()
    if code not in COUPONS:
        return {"ok": False, "error": f"Coupon '{coupon_code}' is invalid."}
    return {"ok": True, "coupon_code": code, "discount_percent": COUPONS[code]}


def calc_shipping(weight_kg: float, destination: str) -> dict[str, Any]:
    """Calculate shipping for a positive total shipment weight in a supported city."""
    if weight_kg <= 0:
        return {"ok": False, "error": "weight_kg must be greater than zero."}
    city = destination.strip().lower()
    base_cost = DESTINATION_RATES.get(city)
    if base_cost is None:
        return {"ok": False, "error": f"Destination '{destination}' is unsupported."}
    extra_kg = max(0.0, weight_kg - 0.5)
    cost = base_cost + round(extra_kg * 20_000)
    return {"ok": True, "destination": destination, "shipping_cost_vnd": cost}


def calculate_order_total(
    unit_price_vnd: float, quantity: int, discount_percent: float, shipping_cost_vnd: float
) -> dict[str, Any]:
    """Calculate a final VND total from already-observed product facts."""
    if quantity <= 0:
        return {"ok": False, "error": "quantity must be greater than zero."}
    if not 0 <= discount_percent <= 100:
        return {"ok": False, "error": "discount_percent must be between 0 and 100."}
    subtotal = round(unit_price_vnd * quantity)
    discount = round(subtotal * discount_percent / 100)
    total = subtotal - discount + round(shipping_cost_vnd)
    return {
        "ok": True,
        "subtotal_vnd": subtotal,
        "discount_vnd": discount,
        "shipping_cost_vnd": round(shipping_cost_vnd),
        "total_vnd": total,
    }


def get_default_tools() -> list[dict[str, Any]]:
    """Return the v2 tool specifications supplied to the LLM."""
    return [
        {
            "name": "check_stock",
            "description": (
                "Checks one product. Input: {\"item_name\": string}. Output includes "
                "available stock, unit_price_vnd and weight_kg. Call this before pricing."
            ),
            "function": check_stock,
            "required_args": ["item_name"],
        },
        {
            "name": "get_discount",
            "description": (
                "Checks one coupon. Input: {\"coupon_code\": string}. Output includes "
                "discount_percent or an invalid-coupon error. Do not invent discounts."
            ),
            "function": get_discount,
            "required_args": ["coupon_code"],
        },
        {
            "name": "calc_shipping",
            "description": (
                "Calculates shipment cost. Input: {\"weight_kg\": number, "
                "\"destination\": string}. weight_kg is the TOTAL order weight and must "
                "come from check_stock multiplied by requested quantity."
            ),
            "function": calc_shipping,
            "required_args": ["weight_kg", "destination"],
        },
        {
            "name": "calculate_order_total",
            "description": (
                "Calculates the final amount only from observed values. Input: "
                "{\"unit_price_vnd\": number, \"quantity\": integer, "
                "\"discount_percent\": number, \"shipping_cost_vnd\": number}. "
                "Returns subtotal_vnd, discount_vnd, and total_vnd."
            ),
            "function": calculate_order_total,
            "required_args": ["unit_price_vnd", "quantity", "discount_percent", "shipping_cost_vnd"],
        },
    ]
