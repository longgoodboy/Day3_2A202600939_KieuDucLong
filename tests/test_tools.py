import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.ecommerce_tools import (
    calc_shipping,
    calculate_order_total,
    check_stock,
    get_discount,
    get_product_details,
    search_products,
)
from src.tools.registry import get_tool_map, get_tool_registry


def test_get_product_details_returns_known_product():
    result = get_product_details("iPhone 15")

    assert result["status"] == "success"
    assert result["error"] is None
    assert result["data"]["name"] == "iPhone 15"
    assert result["data"]["price_vnd"] == 20000000
    assert result["data"]["weight_kg"] == 0.35


def test_get_product_details_handles_unknown_product():
    result = get_product_details("teleportation device")

    assert result["status"] == "error"
    assert result["error"]["code"] == "UNKNOWN_PRODUCT"


def test_check_stock_reports_available_quantity_and_fulfillment():
    result = check_stock("iPhones", requested_quantity=2)

    assert result["status"] == "success"
    assert result["data"]["product_name"] == "iPhone 15"
    assert result["data"]["requested_quantity"] == 2
    assert result["data"]["available_quantity"] == 12
    assert result["data"]["can_fulfill"] is True


def test_check_stock_reports_insufficient_stock():
    result = check_stock("iPhone 15", requested_quantity=100)

    assert result["status"] == "success"
    assert result["data"]["can_fulfill"] is False


def test_check_stock_rejects_invalid_quantity():
    result = check_stock("iPhone 15", requested_quantity=-2)

    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_QUANTITY"


def test_get_discount_handles_active_coupon():
    result = get_discount("winner")

    assert result["status"] == "success"
    assert result["data"]["code"] == "WINNER"
    assert result["data"]["status"] == "active"
    assert result["data"]["discount_percent"] == 10
    assert result["data"]["is_valid"] is True


def test_get_discount_handles_expired_coupon_without_discount():
    result = get_discount("OLD2025")

    assert result["status"] == "success"
    assert result["data"]["status"] == "expired"
    assert result["data"]["discount_percent"] == 0
    assert result["data"]["is_valid"] is False


def test_get_discount_handles_unknown_coupon_without_error():
    result = get_discount("FAKECODE")

    assert result["status"] == "success"
    assert result["data"]["status"] == "unknown"
    assert result["data"]["discount_percent"] == 0
    assert result["data"]["is_valid"] is False


def test_calc_shipping_for_hanoi():
    result = calc_shipping(weight_kg=0.7, destination="Hanoi")

    assert result["status"] == "success"
    assert result["data"]["destination"] == "Hanoi"
    assert result["data"]["shipping_fee_vnd"] == 37000


def test_calc_shipping_for_ho_chi_minh_city_alias():
    result = calc_shipping(weight_kg=1, destination="HCMC")

    assert result["status"] == "success"
    assert result["data"]["destination"] == "Ho Chi Minh City"
    assert result["data"]["shipping_fee_vnd"] == 47000


def test_calc_shipping_rejects_invalid_weight():
    result = calc_shipping(weight_kg=-3, destination="Hanoi")

    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_WEIGHT"


def test_calc_shipping_rejects_unsupported_destination():
    result = calc_shipping(weight_kg=1, destination="Atlantis")

    assert result["status"] == "error"
    assert result["error"]["code"] == "UNSUPPORTED_DESTINATION"


def test_calculate_order_total_returns_transparent_breakdown():
    result = calculate_order_total(
        unit_price=20000000,
        quantity=2,
        discount_percent=10,
        shipping_fee=37000,
    )

    assert result["status"] == "success"
    assert result["data"]["subtotal_vnd"] == 40000000
    assert result["data"]["discount_amount_vnd"] == 4000000
    assert result["data"]["shipping_fee_vnd"] == 37000
    assert result["data"]["final_total_vnd"] == 36037000


def test_calculate_order_total_rejects_invalid_discount():
    result = calculate_order_total(
        unit_price=20000000,
        quantity=2,
        discount_percent=150,
        shipping_fee=37000,
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_DISCOUNT"


def test_search_products_filters_and_sorts_by_price():
    result = search_products(category="headphones", max_price=2000000)

    assert result["status"] == "success"
    assert result["data"]["count"] == 1
    assert result["data"]["products"][0]["name"] == "Wireless Headphones Pro"


def test_search_products_handles_empty_result():
    result = search_products(query="teleportation device")

    assert result["status"] == "success"
    assert result["data"]["count"] == 0
    assert result["data"]["products"] == []


def test_tool_registry_contains_expected_tools():
    registry = get_tool_registry()
    tool_map = get_tool_map()

    expected_names = {
        "search_products",
        "get_product_details",
        "check_stock",
        "get_discount",
        "calc_shipping",
        "calculate_order_total",
    }
    assert {tool["name"] for tool in registry} == expected_names
    assert set(tool_map) == expected_names
    assert all(callable(tool["function"]) for tool in registry)
    assert all(tool["description"] for tool in registry)
    assert all(tool["input_schema"] for tool in registry)
