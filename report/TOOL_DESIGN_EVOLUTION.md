# Tool Design Evolution: v1 to v2

## V1 weakness

The initial tool descriptions were short labels such as “checks stock” and
“calculates shipping.” They did not specify JSON arguments, output fields, or
the dependency between product weight, quantity, and shipping. This makes an
LLM likely to guess argument names or call shipping before it knows the total
weight.

## V2 specification

| Tool | Exact input | Key output | Guardrail |
|---|---|---|---|
| `check_stock` | `{ "item_name": string }` | `stock`, `unit_price_vnd`, `weight_kg` | Call before pricing; check requested quantity against stock. |
| `get_discount` | `{ "coupon_code": string }` | `discount_percent` | Invalid code returns `ok=false`; never make up a rate. |
| `calc_shipping` | `{ "weight_kg": number, "destination": string }` | `shipping_cost_vnd` | Weight must be total order weight and positive. |
| `calculate_order_total` | observed price, quantity, discount, shipping | subtotal/discount/final VND | Prevents LLM arithmetic hallucination. |

## Evidence to collect

Run `python run_agent.py --version v1 ...` and then `--version v2 ...` with
the same request. Compare `logs/*.log`: v2 should have fewer invalid actions
because it states argument schemas and call-order rules explicitly.
