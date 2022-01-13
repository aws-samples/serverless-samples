import json

# helper functions
def build_response(code, body):
    # headers for cors
    headers = {
        # "Access-Control-Allow-Origin": "amazonaws.com",
        # "Access-Control-Allow-Credentials": True,
        "Content-Type": "application/json"
    }
    # lambda proxy integration
    response = {
        "isBase64Encoded": False,
        "statusCode": code,
        "headers": headers,
        "body": body
    }
    return response

def handler(event, context):
    payload = {
        "reqid": event["requestContext"]["requestId"],
        "domain": event["requestContext"]["domainName"],
        "api": event["requestContext"]["apiId"],
        "host": event["headers"]["Host"],
        "path": event["path"],
        "resource": event["resource"],
        "method": event["httpMethod"],
        "x-amzn-vpce-id": event["headers"]["x-amzn-vpce-id"],
        "x-forwarded-for": event["headers"]["X-Forwarded-For"]
    }
    output = build_response(200, json.dumps(payload))
    print(json.dumps(output))
    return output
