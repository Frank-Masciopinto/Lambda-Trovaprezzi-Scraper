from bs4 import BeautifulSoup
import pandas as pd
import os
import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import traceback
import time
import random
import asyncio
import aiohttp
from typing import List, Dict, Any
import os
BASE_API_URL = os.environ.get("BASE_API_URL", "http://172.17.0.1:8000")
print(f"BASE_API_URL: {BASE_API_URL}")
# Try both import styles to ensure compatibility
try:
    # Relative import (should work when module is imported)
    from .request_handler import get_page_content, tls_scraper
except ImportError:
    # Absolute import (should work when run as script)
    from business_manager.scraping_logics.request_handler import (
        get_page_content,
        tls_scraper,
    )


class TrovaPrezziScraper:
    def __init__(self, venditore, categoria=None):
        self.venditore = venditore
        self.categoria = categoria
        self.products = []
        self.total_products = 0
        self.pages_scraped = 0
        self.total_pages = 0
        print(f"Initializing scraper for vendor: {venditore}, category: {categoria}")

    def parse_products(self, response):
        print(f"\nParsing response from: {response.url}")
        print(f"Response status: {response.status}")

        soup = BeautifulSoup(response.text, "html.parser")
        product_names = soup.select("a.item_name")
        product_prices = soup.select("div.item_total_price")

        current_page = response.meta.get("page_number", 1)
        print(f"Processing page {current_page}")
        self.pages_scraped += 1

        if not product_names or not product_prices:
            print(f"No products found on page {current_page}")
            return

        print(f"Found {len(product_names)} products on page {current_page}")

        products_on_page = 0
        for name, price in zip(product_names, product_prices):
            product_name = name.get_text(strip=True)
            price_raw = price.get_text(" ", strip=True)

            import re

            match = re.search(r"((?:\d+\.)*\d+,\d+)", price_raw)
            price_total = match.group(1) if match else price_raw

            product = {
                "Nome Prodotto": product_name,
                "Prezzo Totale": price_total,
                "Nome venditore": self.venditore,
                "URL": response.url,
                "Data Scraping": datetime.now().isoformat(),
                "Pagina": current_page,
            }

            if self.categoria:
                product["nome categoria"] = self.categoria
                product["id categoria"] = self.categoria

            self.products.append(product)
            products_on_page += 1

        self.total_products += products_on_page
        print(f"Page {current_page} completed: {products_on_page} products found")
        print(
            f"Total products so far: {self.total_products} from {self.pages_scraped} pages"
        )

        # Look for the "next" (successivo) button
        # next_button = soup.select_one('div.pagination a[rel="next"]')

        # if next_button and next_button.get("href"):
        #     next_url = f"https://www.trovaprezzi.it{next_button.get('href')}"
        #     print(f"Next page found: {next_url}")

        #     # Request the next page
        #     get_page_content(
        #         url=next_url,
        #         venditore=self.venditore,
        #         categoria=self.categoria,
        #         page_number=current_page + 1,
        #         callback=self.parse_products,
        #         is_first_request=False,
        #     )
        # else:

    def get_start_url(self):
        """
        Generate the starting URL for page 1
        """
        base_url = (
            f"https://www.trovaprezzi.it/negozi/{self.venditore}/offerte#top_page"
        )

        # Handle first page - try without page parameter first
        start_url = (
            f"{base_url}{'?category_id=' + self.categoria if self.categoria else ''}"
        )

        print(f"Starting URL: {start_url}")
        return start_url


async def process_url(
    session: aiohttp.ClientSession, url_entry: Dict[str, Any], venditore: str
) -> Dict[str, Any]:
    """
    Process a single URL asynchronously
    """
    if url_entry["scraped"]:
        print(f"\nSkipping already scraped URL: {url_entry['url']}")
        return url_entry
    scraper = TrovaPrezziScraper(venditore)

    print(f"\nProcessing URL: {url_entry['url']}")
    print(f"Page number: {url_entry['page_number']}")

    try:
        # Start scraping from the current URL
        success = await asyncio.to_thread(
            get_page_content,
            url=url_entry["url"],
            venditore=venditore,
            page_number=url_entry["page_number"],
            callback=scraper.parse_products,
            is_first_request=True,
        )

        if not success:
            print(f"\n=== Error: Could not access URL: {url_entry['url']} ===")
            return url_entry

        # Update the URL entry with scraped data
        url_entry["scraped"] = True
        url_entry["scraped_products"] = len(scraper.products)
        url_entry["products"] = scraper.products
        # add the products to the database onboarding/add-products/
        requests.post(
            f"{BASE_API_URL}/businessManager/onboarding/add-products/",
            json={"business_name": venditore, "products": url_entry},
        )
        print(f"\n=== Page {url_entry['page_number']} Complete ===")
        print(f"Products found: {url_entry['scraped_products']}")

    except Exception as e:
        print(f"\nError processing URL {url_entry['url']}: {str(e)}")
        traceback.print_exc()

    return url_entry


async def process_urls_batch(
    urls: List[Dict[str, Any]], venditore: str, batch_size: int = 20
) -> List[Dict[str, Any]]:
    """
    Process URLs in batches with concurrency control
    """
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            batch_tasks = [
                process_url(session, url_entry, venditore) for url_entry in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks)
            urls[i : i + batch_size] = batch_results
            # Add a small delay between batches to avoid overwhelming the server
            if i + batch_size < len(urls):
                await asyncio.sleep(random.uniform(0.2, 0.5))

        return urls


def run_spider_locally(urls_array: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Function to run the spider locally on an array of URLs
    Each URL in the array should be a dict with:
    {
        "page_number": int,
        "url": str,
        "scraped": bool,
        "scraped_products": int,
        "category_id": str,
        "category_name": str,
        "products": list
    }
    """
    print("\n=== Starting Spider ===")
    print(f"Total URLs to process: {len(urls_array)}")

    try:
        # Initialize scraper with the first URL's vendor name
        first_url = urls_array[0]["url"]
        venditore = first_url.split("/negozi/")[1].split("/")[0]

        # Run the async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        urls_array = loop.run_until_complete(process_urls_batch(urls_array, venditore))
        loop.close()

        # Print final summary
        total_products = sum(entry["scraped_products"] for entry in urls_array)
        scraped_pages = sum(1 for entry in urls_array if entry["scraped"])

        print("\n=== Scraping Complete ===")
        print(f"Total pages processed: {scraped_pages}/{len(urls_array)}")
        print(f"Total products found: {total_products}")

        return {
            "status": "success",
            "total_products": total_products,
            "venditore": venditore,
            "pages_scraped": scraped_pages,
            "urls_data": urls_array,
        }

    except Exception as e:
        print("\n=== Error ===")
        print(f"Error: {str(e)}")
        print("Stack trace:", traceback.format_exc())
        return {"status": "error", "message": str(e), "urls_data": urls_array}


def get_pagination_urls(negozio):
    """
    Iteratively follows the pagination's 'next' button until no next page is available,
    and returns the highest page number found.
    """
    last_page = 1
    page_count = 0
    is_last_page = False
    current_url = f"https://www.trovaprezzi.it/negozi/{negozio}/offerte#top_page"
    try:
        while not is_last_page:
            page_count += 1
            print(f"\n{'='*70}")
            print(f"Fetching page {page_count} for last page detection: {current_url}")

            # Use our TLS scraper instead of requests
            response = tls_scraper.get_page(
                current_url, page_number=page_count, max_retries=100
            )

            if not response:
                print("Failed to fetch page, stopping pagination check")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract all numeric pagination links
            pagination_links = soup.select("div.pagination a")
            page_numbers = [
                int(link.get_text().strip())
                for link in pagination_links
                if link.get_text().strip().isdigit()
            ]
            if page_numbers:
                last_page = max(page_numbers) + 1
                print(f"Found page numbers: {page_numbers}, current max: {last_page}")
            else:
                print("No numeric pagination found, assuming current page is last")
                break

            # Look for the 'next' button (with innertext "Successive")
            pagination_div = soup.find("div", class_="pagination")
            next_button = (
                pagination_div.find("a", string="Successive")
                if pagination_div
                else None
            )
            if next_button and next_button.get("href"):
                next_url = f"https://www.trovaprezzi.it/negozi/{negozio}/offerte?page={last_page}"
                current_url = next_url
                print(f"Found next page button, will check: {next_url}")
            else:
                print("No next button found, reached last page")
                # create array of objects with the page number and the url
                pagination_array = []
                for page in range(1, last_page + 1):
                    pagination_array.append(
                        {
                            "page_number": page,
                            "url": f"https://www.trovaprezzi.it/negozi/{negozio}/offerte?page={page}",
                            "scraped": False,
                            "scraped_products": 0,
                            "products": [],
                        }
                    )
                return pagination_array

    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ ERROR DURING PAGINATION CHECK: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        print(f"Returning current best estimate of last page: {last_page}")
        print(f"{'='*70}")

    print(f"\n{'='*50}")
    print(f"Last page number detected: {last_page}")
    print(f"{'='*50}")
    return last_page


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TrovaPrezzi Scraper")
    parser.add_argument(
        "--venditore", type=str, required=True, help="Nome del venditore"
    )
    parser.add_argument("--categoria", type=str, help="Categoria (optional)")

    args = parser.parse_args()

    print("Starting scraper...")
    pagination_urls_list = get_pagination_urls(args.venditore)
    print(f"Total pages found: {len(pagination_urls_list)}")
    print("Pagination URLs:")
    for page in pagination_urls_list:
        print(f"Page {page['page_number']}: {page['url']}")
    # result = run_spider_locally(args.venditore, args.categoria)
    # print("\nScraping Result:")
    # print(json.dumps(result, indent=2, ensure_ascii=False))
