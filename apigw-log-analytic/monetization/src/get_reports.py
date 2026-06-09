"""
API for retrieving usage reports. Supports listing reports,
filtering by customer/period, and fetching a single report.
"""

import os
import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

REPORTS_TABLE = os.environ["REPORTS_TABLE"]
REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]

table = dynamodb.Table(REPORTS_TABLE)


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    report_id = path_params.get("reportId")

    if report_id:
        return _get_report(report_id)
    return _list_reports(query_params)


def _list_reports(query_params):
    customer_id = query_params.get("customerId")
    billing_period = query_params.get("billingPeriod")

    if customer_id:
        key_expr = "customerId = :cid"
        values = {":cid": customer_id}
        if billing_period:
            key_expr += " AND billingPeriod = :bp"
            values[":bp"] = billing_period
        result = table.query(
            IndexName="customer-period-index",
            KeyConditionExpression=key_expr,
            ExpressionAttributeValues=values,
        )
    else:
        result = table.scan()

    items = _decimals(result.get("Items", []))
    summaries = [{
        "reportId": r["reportId"],
        "customerId": r["customerId"],
        "billingPeriod": r["billingPeriod"],
        "pricingModel": r.get("pricingModel", ""),
        "estimatedTotal": r.get("estimatedTotal", 0),
        "totalRequests": r.get("usage", {}).get("totalRequests", 0),
        "generatedAt": r.get("generatedAt", ""),
    } for r in items]

    return _response(200, {"reports": summaries})


def _get_report(report_id):
    result = table.get_item(Key={"reportId": report_id})
    if "Item" not in result:
        return _response(404, {"error": f"Report '{report_id}' not found"})

    report = _decimals(result["Item"])
    s3_key = f"reports/{report['billingPeriod']}/{report['customerId']}/{report_id}.json"
    try:
        report["downloadUrl"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": REPORTS_BUCKET, "Key": s3_key},
            ExpiresIn=3600,
        )
    except Exception:
        report["downloadUrl"] = None

    return _response(200, report)


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
