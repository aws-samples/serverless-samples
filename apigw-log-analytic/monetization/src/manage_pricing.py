"""
CRUD API for managing pricing plans.

Each plan has a "model" field that determines how usage is calculated:
  - consumption  : flat per-request rate
  - tiered       : volume-based tiers
  - subscription : fixed fee (report shows profitability)
  - freemium     : free quota with paid overage
"""

import os
import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["PRICING_TABLE"])


def handler(event, context):
    method = event["httpMethod"]
    path_params = event.get("pathParameters") or {}
    plan_id = path_params.get("planId")

    if method == "GET" and not plan_id:
        return _list_plans()
    elif method == "GET" and plan_id:
        return _get_plan(plan_id)
    elif method == "POST":
        return _create_plan(event)
    elif method == "PUT" and plan_id:
        return _update_plan(plan_id, event)
    elif method == "DELETE" and plan_id:
        return _delete_plan(plan_id)
    else:
        return _response(405, {"error": "Method not allowed"})


def _list_plans():
    items = table.scan().get("Items", [])
    return _response(200, {"plans": _decimals(items)})


def _get_plan(plan_id):
    result = table.get_item(Key={"planId": plan_id})
    if "Item" not in result:
        return _response(404, {"error": f"Plan '{plan_id}' not found"})
    return _response(200, _decimals(result["Item"]))


def _create_plan(event):
    body = json.loads(event["body"])
    if "planId" not in body:
        return _response(400, {"error": "planId is required"})
    existing = table.get_item(Key={"planId": body["planId"]})
    if "Item" in existing:
        return _response(409, {"error": f"Plan '{body['planId']}' already exists"})
    item = json.loads(json.dumps(body), parse_float=Decimal)
    table.put_item(Item=item)
    return _response(201, body)


def _update_plan(plan_id, event):
    existing = table.get_item(Key={"planId": plan_id})
    if "Item" not in existing:
        return _response(404, {"error": f"Plan '{plan_id}' not found"})
    body = json.loads(event["body"])
    body["planId"] = plan_id
    item = json.loads(json.dumps(body), parse_float=Decimal)
    table.put_item(Item=item)
    return _response(200, body)


def _delete_plan(plan_id):
    table.delete_item(Key={"planId": plan_id})
    return _response(200, {"message": f"Plan '{plan_id}' deleted"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=str),
    }


def _decimals(obj):
    if isinstance(obj, list):
        return [_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj
