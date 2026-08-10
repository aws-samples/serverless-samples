"""
Loads sample pricing plans into DynamoDB — one for each monetization model.

Usage:
  python seed_plans.py <table-name> [--region us-east-1]
"""

import sys
import json
import boto3
from decimal import Decimal

SAMPLE_PLANS = [
    {
        "planId": "payg",
        "planName": "Pay-As-You-Go",
        "model": "consumption",
        "usagePlanName": "PayAsYouGoPlan",
        "perRequestRate": 0.001,
        "perGbRate": 0.10,
    },
    {
        "planId": "tiered",
        "planName": "Tiered Volume",
        "model": "tiered",
        "usagePlanName": "TieredPlan",
        "tiers": [
            {"upTo": 10000, "rate": 0.002},
            {"upTo": 100000, "rate": 0.001},
            {"upTo": 1000000, "rate": 0.0005},
            {"upTo": 999999999, "rate": 0.0002},
        ],
        "perGbRate": 0.08,
    },
    {
        "planId": "pro-subscription",
        "planName": "Pro Subscription",
        "model": "subscription",
        "usagePlanName": "ProPlan",
        "baseFee": 99.00,
        "costPerRequest": 0.0005,
        "perGbRate": 0.06,
    },
    {
        "planId": "free",
        "planName": "Free Tier",
        "model": "freemium",
        "usagePlanName": "FreePlan",
        "freeQuota": 10000,
        "overageRate": 0.003,
        "perGbRate": 0,
    },
]


def main():
    if len(sys.argv) < 2:
        print("Usage: python seed_plans.py <table-name> [--region <region>]")
        sys.exit(1)

    table_name = sys.argv[1]
    region = "us-east-1"
    if "--region" in sys.argv:
        region = sys.argv[sys.argv.index("--region") + 1]

    table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    for plan in SAMPLE_PLANS:
        item = json.loads(json.dumps(plan), parse_float=Decimal)
        table.put_item(Item=item)
        print(f"  loaded: {plan['planId']} ({plan['model']})")

    print(f"\n{len(SAMPLE_PLANS)} plans loaded into {table_name}")


if __name__ == "__main__":
    main()
