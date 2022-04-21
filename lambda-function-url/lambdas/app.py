import json
from urllib.parse import parse_qs

def lambda_handler(event, context):
    devicesmap = {'123456':'Laptop', '654321':'Mobile Phone', '111111':'Desktop'}
    deviceID = 0
    if 'rawQueryString' in event:
        data = parse_qs(event['rawQueryString'])
        if 'deviceID' in data:
            deviceID = data["deviceID"][0]
            if deviceID in devicesmap:
                deviceName = devicesmap[deviceID]
            else:
                deviceName = "Not Found"
            print(data)
            print("found it")
            status = 'FOUND!'
        else:
            deviceID = "PARAMETER NOT FOUND"
            deviceName = "PARAMETER NOT FOUND"
        
    else:
        print("not parameters found")
        deviceID = "NOT FOUND"
        deviceName = "NOT FOUND"
    
    try:
        response = {
            'deviceID': deviceID,
            'deviceName': deviceName
        }
        # return response
        return {
            "statusCode": 200,
            "body": json.dumps(response)
        }
    except Exception as e:
        print(e)
        response['status'] = 400
        response['body'] = []
        return response
        print(e)