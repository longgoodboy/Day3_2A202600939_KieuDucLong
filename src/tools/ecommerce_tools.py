import json
from pathlib import Path
from typing import Any, Dict, Optional


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
) -> Dict[str, Any]:
    """Search products by keyword, category, and optional max VND price."""
    if max_price is not None and max_price < 0:
        return _error("INVALID_PRICE", "max_price must be greater than or equal to 0.")

    normalized_query = _normalize(query) if query else None
    normalized_category = _normalize(category) if category else None
    matches = []

    for product in _load_json("products.json"):
        searchable = " ".join(
            [product["name"], product["category"], *product.get("aliases", [])]
        )
        if normalized_query and normalized_query not in _normalize(searchable):
            continue
        if normalized_category and normalized_category != _normalize(product["category"]):
            continue
        if max_price is not None and product["price_vnd"] > max_price:
            continue
        matches.append(_public_product(product))

    matches.sort(key=lambda item: item["price_vnd"])
    return _success({"count": len(matches), "products": matches})


def get_product_details(item_name: str) -> Dict[str, Any]:
    """Return product ID, normalized name, unit price, weight, and category."""
    product = _find_product(item_name)
    if product is None:
        return _error("UNKNOWN_PRODUCT", f"Unknown product: {item_name}")
    return _success(_public_product(product))


def check_stock(item_name: str, requested_quantity: int = 1) -> Dict[str, Any]:
    """Check available stock and whether requested quantity can be fulfilled."""
    quantity = _coerce_int(requested_quantity)
    if quantity is None or quantity <= 0:
        return _error("INVALID_QUANTITY", "requested_quantity must be a positive integer.")

    product = _find_product(item_name)
    if product is None:
        return _error("UNKNOWN_PRODUCT", f"Unknown product: {item_name}")

    available = int(product["stock"])
    return _success(
        {
            "product_id": product["id"],
            "product_name": product["name"],
            "requested_quantity": quantity,
            "available_quantity": available,
            "can_fulfill": available >= quantity,
        }
    )


def get_discount(coupon_code: str) -> Dict[str, Any]:
    """Return coupon status and discount percentage for active coupons."""
    if not coupon_code or not str(coupon_code).strip():
        return _error("INVALID_COUPON", "coupon_code must be a non-empty string.")

    normalized_code = str(coupon_code).strip().upper()
    for coupon in _load_json("coupons.json"):
        if coupon["code"].upper() == normalized_code:
            is_active = coupon["status"] == "active"
            return _success(
                {
                    "code": coupon["code"],
                    "status": coupon["status"],
                    "discount_percent": coupon["discount_percent"] if is_active else 0,
                    "is_valid": is_active,
                }
            )

    return _success(
        {
            "code": normalized_code,
            "status": "unknown",
            "discount_percent": 0,
            "is_valid": False,
        }
    )


def calc_shipping(weight_kg: float, destination: str) -> Dict[str, Any]:
    """Calculate shipping fee in VND for a supported destination."""
    weight = _coerce_float(weight_kg)
    if weight is None or weight <= 0:
        return _error("INVALID_WEIGHT", "weight_kg must be a positive number.")
    if not destination or not str(destination).strip():
        return _error("INVALID_DESTINATION", "destination must be a non-empty string.")

    rate = _find_shipping_rate(destination)
    if rate is None:
        return _error("UNSUPPORTED_DESTINATION", f"Unsupported destination: {destination}")

    shipping_fee = int(round(rate["base_fee_vnd"] + (rate["fee_per_kg_vnd"] * weight)))
    return _success(
        {
            "destination": rate["destination"],
            "weight_kg": weight,
            "base_fee_vnd": rate["base_fee_vnd"],
            "fee_per_kg_vnd": rate["fee_per_kg_vnd"],
            "shipping_fee_vnd": shipping_fee,
        }
    )


def calculate_order_total(
    unit_price: float,
    quantity: int,
    discount_percent: float,
    shipping_fee: float,
) -> Dict[str, Any]:
    """Calculate subtotal, discount value, shipping, and final total in VND."""
    price = _coerce_float(unit_price)
    qty = _coerce_int(quantity)
    discount = _coerce_float(discount_percent)
    shipping = _coerce_float(shipping_fee)

    if price is None or price < 0:
        return _error("INVALID_PRICE", "unit_price must be greater than or equal to 0.")
    if qty is None or qty <= 0:
        return _error("INVALID_QUANTITY", "quantity must be a positive integer.")
    if discount is None or discount < 0 or discount > 100:
        return _error("INVALID_DISCOUNT", "discount_percent must be between 0 and 100.")
    if shipping is None or shipping < 0:
        return _error("INVALID_SHIPPING", "shipping_fee must be greater than or equal to 0.")

    subtotal = int(round(price * qty))
    discount_amount = int(round(subtotal * (discount / 100)))
    final_total = int(round(subtotal - discount_amount + shipping))

    return _success(
        {
            "unit_price_vnd": int(round(price)),
            "quantity": qty,
            "subtotal_vnd": subtotal,
            "discount_percent": discount,
            "discount_amount_vnd": discount_amount,
            "shipping_fee_vnd": int(round(shipping)),
            "final_total_vnd": final_total,
        }
    )


def _load_json(filename: str) -> list[dict[str, Any]]:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def _find_product(item_name: str) -> Optional[dict[str, Any]]:
    if not item_name or not str(item_name).strip():
        return None
    needle = _normalize(item_name)
    for product in _load_json("products.json"):
        names = [product["name"], *product.get("aliases", [])]
        if any(needle == _normalize(name) or needle in _normalize(name) for name in names):
            return product
    return None


def _find_shipping_rate(destination: str) -> Optional[dict[str, Any]]:
    needle = _normalize(destination)
    for rate in _load_json("shipping_rates.json"):
        names = [rate["destination"], *rate.get("aliases", [])]
        if any(needle == _normalize(name) or needle in _normalize(name) for name in names):
            return rate
    return None


def _public_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_id": product["id"],
        "name": product["name"],
        "category": product["category"],
        "price_vnd": product["price_vnd"],
        "stock": product["stock"],
        "weight_kg": product["weight_kg"],
    }


def _success(data: dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "data": data, "error": None}


def _error(code: str, message: str) -> Dict[str, Any]:
    return {"status": "error", "data": None, "error": {"code": code, "message": message}}


def _normalize(value: Any) -> str:
    return str(value).strip().lower()


def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    try:
        if isinstance(value, float) and not value.is_integer():
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
