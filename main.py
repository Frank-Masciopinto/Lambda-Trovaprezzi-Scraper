import json
from scraping_logics.merchant_info_scraper import scrape_merchant_info
from scraping_logics.seller_products import run_spider_locally
from scraping_logics.url_scheda_prodotto import SchedaProdottoScraper

def handler(event, context):
    """AWS Lambda handler function - Runs scraping directly"""

    query_params = event.get("queryStringParameters", {})
    venditore = query_params.get("venditore", "")
    action = query_params.get("action", "")
    user_id = query_params.get("user_id", "")
    payload = event.get("body", [])
    print(f"Payload: {payload}")
    if action == "scrape_merchant_info":
        if not venditore or not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required parameters"}),
                "headers": {"Content-Type": "application/json"},
            }

        try:
            # Run scraping directly
            result = scrape_merchant_info(venditore)
            # print(f"Scraping completed for {venditore}: {result}")

            # Ensure the result is JSON serializable
            response_body = {
                "message": "Scraping completed",
                # "data": result
            }

            return {
                "statusCode": 200,
                "body": json.dumps(response_body),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",  # Add CORS header
                },
            }

        except Exception as e:
            print(f"Error in scraping {venditore}: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",  # Add CORS header
                },
            }
    elif action == "scrape_seller_products_by_category":
        if not payload:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required payload"}),
                "headers": {"Content-Type": "application/json"},
            }
        try:
            run_spider_locally(payload)
        except Exception as e:
            print(f"Error in scraping {venditore}: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)}),
                "headers": {"Content-Type": "application/json"},
            }
    elif action == "scrape_scheda_prodotto":
        try:
            titolo_prodotto = payload.get("titolo_prodotto", "")
            categoria_id = payload.get("categoria_id", "")
            scraper = SchedaProdottoScraper(titolo_prodotto, categoria_id)
            result = scraper.estrai_dati_pagina()
            return {
                "statusCode": 200,
                "body": json.dumps(result),
                "headers": {"Content-Type": "application/json"},
            }
        except Exception as e:
            print(f"Error in scraping {venditore}: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)}),
                "headers": {"Content-Type": "application/json"},
            }
