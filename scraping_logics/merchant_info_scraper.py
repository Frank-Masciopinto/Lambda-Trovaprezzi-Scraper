from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests

try:
    from .request_handler import tls_scraper
except ImportError:
    from business_manager.scraping_logics.request_handler import tls_scraper

class MerchantInfoScraper:
    """Scraper for merchant information from TrovaPrezzi"""
    
    def __init__(self, venditore: str):
        self.venditore = venditore
        self.base_url = f"https://www.trovaprezzi.it/negozi/{venditore}#top_page"
        self.merchant_all_categories_url = f"https://www.trovaprezzi.it/negozi/{venditore}/categorie"
        self.add_merchant_info_url = "http://172.17.0.1:8000/businessManager/onboarding/add-merchant-info/"
        self.merchant_data = {}
        print(f"Initializing merchant info scraper for: {venditore}")
    
    def extract_rating_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract rating information from the page"""
        rating_data = {}
        
        try:
            rating_wrapper = soup.select_one('div.last_year_rating_wrapper')
            if rating_wrapper:
                # Get rating image info
                rating_image = rating_wrapper.select_one('.rating_image')
                if rating_image:
                    rating_data['rating_title'] = rating_image.get('title', '')
                    rating_data['rating_value'] = rating_image.get_text(strip=True)

                # Get rating number
                rate_nr = rating_wrapper.select_one('.rate_nr')
                if rate_nr:
                    rating_data['rate_nr'] = rate_nr.get_text(strip=True)

                # Get review counter
                counter = rating_wrapper.select_one('.counter')
                if counter:
                    rating_data['review_counter'] = counter.get_text(strip=True)
            else:
                rating_data['error'] = 'Rating wrapper not found'

        except Exception as e:
            rating_data['error'] = f'Error extracting rating info: {str(e)}'
            print(f"❌ Error extracting rating: {str(e)}")

        return rating_data

    def extract_merchant_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract merchant information from the page"""
        merchant_info = {
            "business_name": self.venditore,
            "scraping_date": datetime.now().isoformat()
        }

        try:
            # Extract website
            website_link = soup.select_one('a[data-ga-action="website"]')
            if website_link:
                merchant_info["indirizzo web"] = website_link.get('href', '')

            # Extract merchant data section
            dati_mercante = soup.select_one('section.single_section_merchant')
            if dati_mercante:
                # Find all table rows
                rows = dati_mercante.select('div.table_row')
                for row in rows:
                    # Find label cell and value cell in each row
                    label_cell = row.select_one('div.label_cell')
                    value_cell = row.select_one('div.info_cell')
                    if label_cell and value_cell:
                        label = label_cell.get_text(strip=True)
                        value = value_cell.get_text(strip=True)
                        if label == "Indirizzo web":
                            merchant_info["domain"] = value
                        elif label == "E-mail di riferimento":
                            merchant_info["email"] = value
                        elif label == "Indirizzo postale":
                            merchant_info["address"] = value
                        elif label == "Telefono":
                            merchant_info["phone"] = value
                        # You can add more labels to extract here

            # Extract contact info
            contact_info = soup.select_one('div.merchant_contact_info')
            if contact_info:
                # Phone
                phone = contact_info.select_one('div.phone')
                if phone:
                    merchant_info["telefono"] = phone.get_text(strip=True)

                # Email
                email = contact_info.select_one('div.email')
                if email:
                    merchant_info["e-mail di riferimento"] = email.get_text(strip=True)

                # Address
                address = contact_info.select_one('div.address')
                if address:
                    merchant_info["indirizzo postale"] = address.get_text(strip=True)

            # Extract description
            description = soup.select_one('p.merchant_description_info')
            if description:
                merchant_info["merchant_description_info"] = description.get_text(strip=True)

        except Exception as e:
            merchant_info['error'] = f'Error extracting merchant info: {str(e)}'
            print(f"❌ Error extracting merchant info: {str(e)}")

        return merchant_info

    def extract_logo_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract merchant logo information from the page"""
        logo_data = {}
        
        try:
            logo_img = soup.select_one('img.merchant_logo')
            if logo_img:
                logo_data['logo'] = logo_img.get('src', '')
                # Get additional attributes if they exist
                logo_data['logo_alt'] = logo_img.get('alt', '')
                logo_data['logo_title'] = logo_img.get('title', '')
            else:
                logo_data['logo'] = None
                print("⚠️ No merchant logo found")

        except Exception as e:
            logo_data['logo'] = None
            logo_data['error'] = f'Error extracting logo info: {str(e)}'
            print(f"❌ Error extracting logo: {str(e)}")

        return logo_data

    def send_merchant_data(self) -> Dict[str, Any]:
        """Send merchant data to the API"""
        if not self.merchant_data:
            return {
                "status": "error",
                "message": "No merchant data to send"
            }

        try:
            response = requests.post(
                self.add_merchant_info_url,
                json={
                    "business_name": self.venditore,
                    "merchant_data": self.merchant_data,
                    "categories": self.merchant_categories
                }
            )

            if response.status_code in (200, 201):
                print("✅ Merchant data sent successfully")
                return response.json()
            else:
                print(f"❌ Failed to send merchant data. Status: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"API request failed with status {response.status_code}"
                }

        except Exception as e:
            error_msg = f"Error sending merchant data: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg
            }

    def extract_merchant_categories(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract merchant categories from the page"""
        categories = []
        category_list = soup.select("div.three_columns_list ul li")
        
        for li in category_list:
            link = li.find('a')
            if link:
                results_span = li.select_one('span.results_number')
                results_count = results_span.text.strip('()') if results_span else '0'
                category_id = link.get('href', '').split('category_id=')[1]
                
                # Calculate pages using ceiling division
                total_results = int(results_count)
                pages = (total_results + 19) // 20  # This ensures at least 1 page if there are products
                
                category = {
                    'title': link.get('title', ''),
                    'href': link.get('href', ''),
                    'category_id': category_id,
                    'count': total_results,
                    'pages': max(1, pages)  # Ensure at least 1 page
                }
                categories.append(category)
        print("all categories: ", categories)
        return categories

    def scrape(self) -> Dict[str, Any]:
        """Main scraping method"""
        scrape_result = self._scrape()
        if scrape_result['status'] == 'success':
            # Send data to API
            categories_result = self._scrape_categories()
            api_result = self.send_merchant_data()

            return {
                "status": "success",
                "data": self.merchant_data,
                "categories": categories_result
            }

        return scrape_result

    def _scrape(self) -> Dict[str, Any]:
        """Internal scraping method"""
        print(f"\n{'='*70}")
        print(f"Starting merchant info scrape for: {self.venditore}")
        print(f"URL: {self.base_url}")
        
        try:
            # Get the page using TLS client
            response = tls_scraper.get_page(self.base_url, max_retries=100)
            
            if not response or response.status != 200:
                print(f"❌ Failed to get page. Status: {getattr(response, 'status', 'Unknown')}")
                return {"status": "error", "message": "Failed to fetch page"}

            # Parse the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all information
            merchant_info = self.extract_merchant_info(soup)
            rating_info = self.extract_rating_info(soup)
            logo_info = self.extract_logo_info(soup)
            
            # Combine the data
            self.merchant_data = {**merchant_info, **rating_info, **logo_info}
            
            # Print the results
            print("\n📊 Merchant Information:")
            print(json.dumps(self.merchant_data, indent=2, ensure_ascii=False))
            
            return {
                "status": "success",
                "data": self.merchant_data
            }

        except Exception as e:
            error_msg = f"Error scraping merchant info: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg
            }
        
    def _scrape_categories(self) -> Dict[str, Any]:
        """Internal scraping method"""
        print(f"\n{'='*70}")
        print(f"Starting merchant categories scrape for: {self.venditore}")
        print(f"URL: {self.merchant_all_categories_url}")
        
        try:
            # Get the page using TLS client
            response = tls_scraper.get_page(self.merchant_all_categories_url, max_retries=100)
            
            if not response or response.status != 200:
                print(f"❌ Failed to get page. Status: {getattr(response, 'status', 'Unknown')}")
                return {"status": "error", "message": "Failed to fetch page"}

            # Parse the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all information
            merchant_categories = self.extract_merchant_categories(soup)
            
            # Store the categories list directly (no need to unpack)
            self.merchant_categories = merchant_categories
            
            # Print the results
            print("\n📊 Merchant categories:")
            print(json.dumps(merchant_categories, indent=2, ensure_ascii=False))
            
            return {
                "status": "success",
                "data": merchant_categories  # Return the list directly
            }

        except Exception as e:
            error_msg = f"Error scraping merchant categories: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg
            }

def scrape_merchant_info(venditore: str) -> Dict[str, Any]:
    """Convenience function to scrape merchant info"""
    scraper = MerchantInfoScraper(venditore)
    return scraper.scrape()
