"""
Generates a usage report for a single API customer/tenant.

Looks up the customer's pricing plan and calculates estimated charges
based on actual API usage from access logs. The report is close enough
to an invoice that it can be tailored into one.

Supported pricing models:
  - consumption : Pay per request at a flat rate
  - tiered      : Rate decreases at higher volumes
  - subscription: Fixed fee with included quota — report shows profitability
  - freemium    : Free quota with optional paid overage
"""

import os
import json
import uuid
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

PRICING_TABLE = os.environ["PRICING_TABLE"]
REPORTS_TABLE = os.environ["REPORTS_TABLE"]
REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]

pricing_table = dynamodb.Table(PRICING_TABLE)
reports_table = dynamodb.Table(REPORTS_TABLE)

DEFAULT_PRICING = {
    "planId": "default",
    "planName": "Pay-As-You-Go",
    "model": "consumption",
    "perRequestRate": 0.001,
    "perGbRate": 0.10,
}


def handler(event, context):
    customer = event["customer"]
    billing_period = event["billingPeriod"]
    customer_id = customer["customerId"]
    usage_plan = customer.get("usagePlan", "default")

    pricing = _get_pricing(usage_plan)
    model = pricing.get("model", "consumption")

    # Calculate charges based on the pricing model
    if model == "tiered":
        line_items = _calc_tiered(pricing, customer)
    elif model == "subscription":
        line_items = _calc_subscription(pricing, customer)
    elif model == "freemium":
        line_items = _calc_freemium(pricing, customer)
    else:
        line_items = _calc_consumption(pricing, customer)

    # Add data transfer if configured
    line_items += _calc_data_transfer(pricing, customer)

    estimated_total = round(sum(item["amount"] for item in line_items), 2)

    report = {
        "reportId": f"RPT-{billing_period}-{customer_id}-{uuid.uuid4().hex[:8]}",
        "customerId": customer_id,
        "apiKeyId": customer.get("apiKeyId", ""),
        "usagePlan": usage_plan,
        "billingPeriod": billing_period,
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "pricingModel": model,
        "pricingPlan": pricing.get("planName", pricing["planId"]),
        "usage": {
            "totalRequests": customer["totalRequests"],
            "successfulRequests": customer["totalSuccessful"],
            "errorRequests": customer["totalErrors"],
            "totalResponseBytes": customer["totalResponseBytes"],
            "routes": customer.get("routes", []),
        },
        "lineItems": line_items,
        "estimatedTotal": estimated_total,
        "currency": "USD",
    }

    # For subscription model, add profitability section
    if model == "subscription":
        base_fee = float(pricing.get("baseFee", 0))
        report["profitability"] = {
            "subscriptionFee": base_fee,
            "estimatedCostToServe": estimated_total,
            "margin": round(base_fee - estimated_total, 2),
            "profitable": base_fee >= estimated_total,
        }

    # Store report
    _store_report(report)

    s3_key = f"reports/{billing_period}/{customer_id}/{report['reportId']}.json"
    s3.put_object(
        Bucket=REPORTS_BUCKET,
        Key=s3_key,
        Body=json.dumps(report, indent=2, default=str),
        ContentType="application/json",
    )

    return {
        "reportId": report["reportId"],
        "customerId": customer_id,
        "pricingModel": model,
        "estimatedTotal": estimated_total,
    }


# ---------------------------------------------------------------------------
# Pricing model calculations
# ---------------------------------------------------------------------------

def _calc_consumption(pricing, customer):
    """Flat rate per request."""
    rate = float(pricing.get("perRequestRate", 0.001))
    reqs = customer["totalRequests"]
    return [{
        "description": f"{reqs:,} API requests @ ${rate}/req",
        "quantity": reqs,
        "unitPrice": rate,
        "amount": round(reqs * rate, 2),
    }]


def _calc_tiered(pricing, customer):
    """Volume tiers — rate drops at higher usage."""
    items = []
    remaining = customer["totalRequests"]
    prev = 0
    for tier in sorted(pricing.get("tiers", []), key=lambda t: int(t["upTo"])):
        up_to = int(tier["upTo"])
        rate = float(tier["rate"])
        tier_size = up_to - prev
        qty = min(remaining, tier_size)
        if qty <= 0:
            break
        items.append({
            "description": f"Requests {prev + 1:,}–{prev + qty:,} @ ${rate}/req",
            "quantity": qty,
            "unitPrice": rate,
            "amount": round(qty * rate, 2),
        })
        remaining -= qty
        prev = up_to
    return items


def _calc_subscription(pricing, customer):
    """
    Subscription reports show cost-to-serve, not a bill.
    The API owner pays a flat fee — this shows whether they're profitable.
    """
    # Estimate what it would cost at a per-request rate
    cost_rate = float(pricing.get("costPerRequest", 0.0005))
    reqs = customer["totalRequests"]
    return [{
        "description": f"Estimated cost to serve {reqs:,} requests @ ${cost_rate}/req",
        "quantity": reqs,
        "unitPrice": cost_rate,
        "amount": round(reqs * cost_rate, 2),
    }]


def _calc_freemium(pricing, customer):
    """Free quota, then paid overage."""
    items = []
    free_quota = int(pricing.get("freeQuota", 10000))
    reqs = customer["totalRequests"]
    free_used = min(reqs, free_quota)

    items.append({
        "description": f"Free tier: {free_used:,} of {free_quota:,} requests",
        "quantity": free_used,
        "unitPrice": 0,
        "amount": 0,
    })

    overage = max(0, reqs - free_quota)
    if overage > 0:
        rate = float(pricing.get("overageRate", 0.002))
        items.append({
            "description": f"Overage: {overage:,} requests @ ${rate}/req",
            "quantity": overage,
            "unitPrice": rate,
            "amount": round(overage * rate, 2),
        })
    return items


def _calc_data_transfer(pricing, customer):
    """Data transfer charge (shared across all models)."""
    gb_rate = float(pricing.get("perGbRate", 0))
    total_gb = customer["totalResponseBytes"] / (1024 ** 3)
    if total_gb > 0 and gb_rate > 0:
        return [{
            "description": f"Data transfer: {total_gb:.4f} GB @ ${gb_rate}/GB",
            "quantity": round(total_gb, 6),
            "unitPrice": gb_rate,
            "amount": round(total_gb * gb_rate, 2),
        }]
    return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_pricing(usage_plan):
    resp = pricing_table.get_item(Key={"planId": usage_plan})
    if "Item" in resp:
        return resp["Item"]
    scan = pricing_table.scan(
        FilterExpression="usagePlanName = :up",
        ExpressionAttributeValues={":up": usage_plan},
    )
    if scan["Items"]:
        return scan["Items"][0]
    return DEFAULT_PRICING


def _store_report(report):
    item = json.loads(json.dumps(report, default=str), parse_float=Decimal)
    reports_table.put_item(Item=item)
