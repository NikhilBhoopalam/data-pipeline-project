def lambda_handler(event, context):
    print("Lambda triggered, event:", event)
    return {"statusCode": 200}
