"""
Queries API Gateway access logs via Athena to aggregate usage per
customer (API key) for a billing period. Returns per-customer usage
broken down by route, method, and status code.
"""

import os
import time
import boto3
from datetime import datetime, timedelta

athena = boto3.client("athena")

GLUE_DATABASE = os.environ["GLUE_DATABASE"]
PROJECT_NAME = os.environ["PROJECT_NAME"]
ACCESS_LOGS_BUCKET = os.environ["ACCESS_LOGS_BUCKET"]

ATHENA_OUTPUT = f"s3://{PROJECT_NAME}-athena-results-{boto3.client('sts').get_caller_identity()['Account']}/"


def handler(event, context):
    billing_period = _resolve_billing_period(event)
    year, month = billing_period.split("-")

    query = f"""
        SELECT
            "identity.apikeyname" AS customer_name,
            identityapikeyid       AS api_key_id,
            "identity.usageplanname" AS usage_plan,
            routekey               AS route,
            httpmethod             AS method,
            status,
            COUNT(*)               AS request_count,
            AVG(CAST(responselatency AS double))  AS avg_latency_ms,
            SUM(CAST(responselength AS bigint))   AS total_response_bytes
        FROM logs
        WHERE year = '{year}' AND month = '{month}'
          AND "identity.apikeyname" != '-'
          AND status IS NOT NULL
        GROUP BY
            "identity.apikeyname",
            identityapikeyid,
            "identity.usageplanname",
            routekey,
            httpmethod,
            status
        ORDER BY customer_name, request_count DESC
    """

    execution_id = _run_query(query)
    rows = _get_results(execution_id)
    customers = _aggregate(rows, billing_period)

    return {"customers": customers, "billingPeriod": billing_period}


def _resolve_billing_period(event):
    if "billingPeriod" in event:
        return event["billingPeriod"]
    first = datetime.utcnow().replace(day=1)
    prev = first - timedelta(days=1)
    return prev.strftime("%Y-%m")


def _run_query(query):
    resp = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": GLUE_DATABASE},
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT},
    )
    return resp["QueryExecutionId"]


def _get_results(execution_id, max_wait=120):
    elapsed = 0
    while elapsed < max_wait:
        resp = athena.get_query_execution(QueryExecutionId=execution_id)
        state = resp["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in ("FAILED", "CANCELLED"):
            reason = resp["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
            raise RuntimeError(f"Athena query {state}: {reason}")
        time.sleep(2)
        elapsed += 2

    rows = []
    paginator = athena.get_paginator("get_query_results")
    for page in paginator.paginate(QueryExecutionId=execution_id):
        for row in page["ResultSet"]["Rows"]:
            rows.append([col.get("VarCharValue", "") for col in row["Data"]])
    return rows


def _aggregate(rows, billing_period):
    if len(rows) <= 1:
        return []

    header = rows[0]
    customers = {}

    for row in rows[1:]:
        rec = dict(zip(header, row))
        name = rec["customer_name"]
        if name not in customers:
            customers[name] = {
                "customerId": name,
                "apiKeyId": rec["api_key_id"],
                "usagePlan": rec["usage_plan"],
                "billingPeriod": billing_period,
                "routes": [],
                "totalRequests": 0,
                "totalSuccessful": 0,
                "totalErrors": 0,
                "totalResponseBytes": 0,
            }

        count = int(rec["request_count"])
        status = int(rec["status"]) if rec["status"] else 0
        resp_bytes = int(rec["total_response_bytes"]) if rec["total_response_bytes"] else 0

        customers[name]["routes"].append({
            "route": rec["route"],
            "method": rec["method"],
            "status": rec["status"],
            "requestCount": count,
            "avgLatencyMs": round(float(rec["avg_latency_ms"]), 2) if rec["avg_latency_ms"] else 0,
            "totalResponseBytes": resp_bytes,
        })
        customers[name]["totalRequests"] += count
        customers[name]["totalResponseBytes"] += resp_bytes
        if 200 <= status < 400:
            customers[name]["totalSuccessful"] += count
        else:
            customers[name]["totalErrors"] += count

    return list(customers.values())
