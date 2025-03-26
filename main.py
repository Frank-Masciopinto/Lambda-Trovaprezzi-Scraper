import json
from scraping_logics.merchant_info_scraper import scrape_merchant_info

def handler(event, context):
    """AWS Lambda handler function - Runs scraping directly"""

    query_params = event.get("queryStringParameters", {})
    venditore = query_params.get("venditore", "")

    if not venditore:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'venditore' parameter."}),
            "headers": {"Content-Type": "application/json"},
        }

    try:
        # Run scraping directly
        result = scrape_merchant_info(venditore)
        print(f"Scraping completed for {venditore}: {result}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Scraping completed", "data": result}),
            "headers": {"Content-Type": "application/json"},
        }

    except Exception as e:
        print(f"Error in scraping {venditore}: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }
