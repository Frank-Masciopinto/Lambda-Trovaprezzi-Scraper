import json
import boto3
from scraping_logics.merchant_info_scraper import scrape_merchant_info

lambda_client = boto3.client("lambda")

def handler(event, context):
    """AWS Lambda handler function"""
    
    # Check if it's an async invocation (Lambda calling itself)
    if "venditore" in event:
        venditore = event["venditore"]
        
        try:
            result = scrape_merchant_info(venditore)
            print(f"Scraping completed for {venditore}: {result}")
        except Exception as e:
            print(f"Error in scraping {venditore}: {str(e)}")

        return {"statusCode": 200, "body": json.dumps({"message": "Scraping completed"})}

    # Normal API Gateway invocation
    event_name = event.get("queryStringParameters", {}).get("event_name", "")
    venditore = event.get("queryStringParameters", {}).get("venditore", "")

    if event_name == "scrape_merchant_info":
        # Call Lambda asynchronously to handle scraping
        payload = json.dumps({"venditore": venditore})
        
        lambda_client.invoke(
            FunctionName=context.function_name,  # Calls itself
            InvocationType="Event",  # Asynchronous execution
            Payload=payload
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Scraping started for merchant: {venditore}"}),
            "headers": {"Content-Type": "application/json"},
        }
    
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid event name"}),
            "headers": {"Content-Type": "application/json"},
        }
