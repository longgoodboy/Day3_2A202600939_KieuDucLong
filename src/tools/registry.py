from typing import Any, Callable, Dict, List

from src.tools.ecommerce_tools import (
    calc_shipping,
    calculate_order_total,
    check_stock,
    get_discount,
    get_product_details,
    search_products,
)


ToolSpec = Dict[str, Any]


def get_tool_registry() -> List[ToolSpec]:
    """Return registered e-commerce tools with strict descriptions."""
    return [
        {
            "name": "search_products",
            "description": (
                "Search the local product catalog by optional query, category, and max_price "
                "in VND. Returns sorted matching products or an empty result."
            ),
            "function": search_products,
            "input_schema": {
                "query": "optional string",
                "category": "optional string",
                "max_price": "optional number >= 0",
            },
        },
        {
            "name": "get_product_details",
            "description": (
                "Get product ID, normalized product name, category, unit price in VND, "
                "stock, and package weight in kilograms. Required argument: item_name."
            ),
            "function": get_product_details,
            "input_schema": {"item_name": "required string"},
        },
        {
            "name": "check_stock",
            "description": (
                "Check available quantity for a product and whether requested_quantity can "
                "be fulfilled. Required: item_name. Optional: requested_quantity positive integer."
            ),
            "function": check_stock,
            "input_schema": {
                "item_name": "required string",
                "requested_quantity": "optional positive integer",
            },
        },
        {
            "name": "get_discount",
            "description": (
                "Check coupon status. Returns active, expired, or unknown status and only "
                "returns a positive discount for active coupons. Required: coupon_code."
            ),
            "function": get_discount,
            "input_schema": {"coupon_code": "required string"},
        },
        {
            "name": "calc_shipping",
            "description": (
                "Calculate shipping fee in VND using positive weight_kg and supported "
                "Vietnamese destination. Returns structured error for unsupported cities."
            ),
            "function": calc_shipping,
            "input_schema": {
                "weight_kg": "required positive number",
                "destination": "required string",
            },
        },
        {
            "name": "calculate_order_total",
            "description": (
                "Calculate subtotal, discount amount, shipping fee, and final total in VND. "
                "Requires unit_price, quantity, discount_percent, and shipping_fee."
            ),
            "function": calculate_order_total,
            "input_schema": {
                "unit_price": "required number >= 0",
                "quantity": "required positive integer",
                "discount_percent": "required number between 0 and 100",
                "shipping_fee": "required number >= 0",
            },
        },
    ]


def get_tool_map() -> Dict[str, Callable[..., Dict[str, Any]]]:
    """Return registered tools keyed by tool name."""
    return {tool["name"]: tool["function"] for tool in get_tool_registry()}
