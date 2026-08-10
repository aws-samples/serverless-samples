"""
Compiles individual customer reports into a consolidated billing file.
Produces both JSON and CSV formats, stored in S3 with presigned download URLs.

Called as the final step in the billing workflow after all per-customer
reports have been generated.
"""

import os
import io
import csv
import json
import boto3
from datetime import datetime

s3 = boto3.client("s3")

REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]


def handler(event, context):
    billing_period = event["billingPeriod"]
    report_summaries = event.get("reportSummaries", [])

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    base_key = f"reports/{billing_period}/consolidated/billing-report-{timestamp}"

    # Build consolidated data
    consolidated = {
        "billingPeriod": billing_period,
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "totalCustomers": len(report_summaries),
        "grandTotal": round(sum(r.get("estimatedTotal", 0) for r in report_summaries), 2),
        "currency": "USD",
        "customers": report_summaries,
    }

    # Upload JSON
    json_key = f"{base_key}.json"
    s3.put_object(
        Bucket=REPORTS_BUCKET,
        Key=json_key,
        Body=json.dumps(consolidated, indent=2, default=str),
        ContentType="application/json",
    )

    # Upload CSV
    csv_key = f"{base_key}.csv"
    csv_body = _build_csv(report_summaries, billing_period)
    s3.put_object(
        Bucket=REPORTS_BUCKET,
        Key=csv_key,
        Body=csv_body,
        ContentType="text/csv",
    )

    # Generate presigned download URLs (valid 1 hour)
    json_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": REPORTS_BUCKET, "Key": json_key}, ExpiresIn=3600
    )
    csv_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": REPORTS_BUCKET, "Key": csv_key}, ExpiresIn=3600
    )

    return {
        "billingPeriod": billing_period,
        "totalCustomers": len(report_summaries),
        "grandTotal": consolidated["grandTotal"],
        "files": {
            "json": {"bucket": REPORTS_BUCKET, "key": json_key, "downloadUrl": json_url},
            "csv": {"bucket": REPORTS_BUCKET, "key": csv_key, "downloadUrl": csv_url},
        },
    }


def _build_csv(report_summaries, billing_period):
    """Build a CSV string from report summaries."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["billing_period", "customer_id", "pricing_model", "estimated_total", "currency", "report_id"])

    for r in report_summaries:
        writer.writerow([
            billing_period,
            r.get("customerId", ""),
            r.get("pricingModel", ""),
            r.get("estimatedTotal", 0),
            "USD",
            r.get("reportId", ""),
        ])

    return output.getvalue()
