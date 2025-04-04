import json
from scraping_logics.merchant_info_scraper import scrape_merchant_info
from scraping_logics.seller_products import run_spider_locally
from scraping_logics.url_scheda_prodotto import SchedaProdottoScraper
import asyncio
import traceback

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
    elif action == "scrape_products_competitors":
        try:
            scraping_job = payload.get("scraping_job", {})
            # get the products from the scraping job
            print(scraping_job)
            products = scraping_job.get("products", [])

            async def scrape_product(product):
                titolo_prodotto = product.get("name", "")
                categoria_id = product.get("category", {}).get("id", "")
                scheda_prodotto = product.get("scheda_prodotto", None)
                scraper = SchedaProdottoScraper(
                    titolo_prodotto, categoria_id, scheda_prodotto
                )
                
                if scheda_prodotto:
                    print(f"Scheda prodotto already scraped for {titolo_prodotto}")
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        scraper.estrai_dati_competitor
                    )
                else:
                    print(f"Scraping scheda prodotto for {titolo_prodotto}")
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        scraper.cerca_scheda_prodotto_estrai_dati_competitor
                    )
                #only keep id and result_data
                result = {
                    "product_id": product.get("id", ""),
                    "scraping_result": result
                }
                return result

            # Create and run all tasks concurrently
            loop = asyncio.get_event_loop()
            tasks = [scrape_product(product) for product in products]
            results = loop.run_until_complete(asyncio.gather(*tasks))
            scraping_job['result_data'] = results
            print(f"All results (products with competitor data): {results}")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
            }
        except Exception as e:
            traceback.print_exc()
            print(f"Error in scraping {venditore}: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)}),
                "headers": {"Content-Type": "application/json"},
            }
