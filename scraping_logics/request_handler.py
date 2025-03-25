from scrapy import Spider, Request
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from twisted.internet.error import (
    ConnectionLost,
    ConnectionDone,
    ConnectError,
    TimeoutError,
)
from twisted.web.client import ResponseFailed
import os
import json
import random
import scrapy.spidermiddlewares.httperror
from twisted.internet.task import deferLater  # NEW import
import tls_client
import requests
import traceback
import secrets
import asyncio
from datetime import datetime
from .configs.user_agents import chrome122_user_agents, chrome121_user_agents, chrome120_user_agents
import hashlib
from .configs.languages import lang_IT_headers
import time
# For handling responses from various libraries
class CustomResponse:
    """A custom response wrapper for compatibility between different HTTP libraries"""

    def __init__(self, requests_resp):
        self.status_code = requests_resp.status_code
        self.content = requests_resp.content
        self.headers = requests_resp.headers
        self.text = requests_resp.text


# Replace namedtuple with a proper class
class ScraperResponse:
    """A response-like object for compatibility with existing callbacks"""

    def __init__(self, url, text, status, meta=None, headers=None):
        self.url = url
        self.text = text
        self.status = status
        self.meta = meta or {}
        self.headers = headers or {}
        # Add body property for compatibility with Scrapy responses
        self.body = text.encode("utf-8") if isinstance(text, str) else text


def generate_browser_fingerprint():
    """
    Generates a highly realistic browser fingerprint that closely matches real Chrome browser behavior
    """
    # Screen and window dimensions with realistic ratios and common resolutions
    common_resolutions = [
        # Most common desktop resolutions
        (1920, 1080),  # Full HD
        (1366, 768),   # Laptop
        (1536, 864),   # 2K
        (1440, 900),   # WXGA+
        (1280, 720),   # HD
        (1600, 900),   # HD+
        (2560, 1440),  # 2K
        (3840, 2160),  # 4K
        # Additional common resolutions
        (1680, 1050),  # WSXGA+
        (1920, 1200),  # WUXGA
        (2560, 1600),  # WQXGA
        (2880, 1800),  # Retina
        (3200, 1800),  # QHD+
        (3840, 2400),  # WQUXGA
    ]
    screen_dims = random.choice(common_resolutions)
    
    # Calculate realistic viewport dimensions (slightly smaller than screen)
    # Chrome's default UI elements take up space
    chrome_ui_height = random.randint(60, 120)  # Address bar, tabs, etc.
    chrome_ui_width = random.randint(20, 50)    # Scrollbar, etc.
    viewport_width = screen_dims[0] - chrome_ui_width
    viewport_height = screen_dims[1] - chrome_ui_height
    
    # Realistic color depth and pixel depth based on modern displays
    color_depth = random.choice([24, 30, 48])  # 24-bit, 30-bit, or 48-bit color
    pixel_depth = color_depth  # Usually matches color depth
    
    # Device memory and hardware concurrency based on common configurations
    device_memory = random.choice([4, 8, 16, 32, 64])  # Common RAM sizes
    hardware_concurrency = random.choice([4, 6, 8, 12, 16, 24, 32])  # Common CPU core counts
    
    # Platform and architecture with realistic combinations
    platform_choices = [
        # Windows configurations
        ('Windows', 'Win64; x64'),
        ('Windows', 'Win64; x64; rv:122.0'),
        ('Windows', 'Win64; x64; rv:121.0'),
        # macOS configurations
        ('Macintosh', 'Intel Mac OS X 10_15_7'),
        ('Macintosh', 'Intel Mac OS X 11_2_3'),
        ('Macintosh', 'Intel Mac OS X 12_3_1'),
        # Linux configurations
        ('X11', 'Linux x86_64'),
        ('X11', 'Linux x86_64; rv:122.0'),
        ('X11', 'Linux x86_64; rv:121.0'),
    ]
    platform, platform_details = random.choice(platform_choices)
    
    # WebGL parameters with realistic GPU combinations
    webgl_vendor = random.choice([
        # NVIDIA GPUs
        "Google Inc. (NVIDIA)",
        "NVIDIA Corporation",
        # AMD GPUs
        "Google Inc. (AMD)",
        "AMD Corporation",
        # Intel GPUs
        "Google Inc. (Intel)",
        "Intel Inc.",
        # Apple GPUs
        "Apple GPU",
        "Apple M1",
        "Apple M2",
        "Apple M3"
    ])
    
    webgl_renderer = random.choice([
        # NVIDIA GPUs
        "ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0)",
        "ANGLE (NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0)",
        "ANGLE (NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0)",
        # AMD GPUs
        "ANGLE (AMD Radeon RX 6800 XT Direct3D11 vs_5_0)",
        "ANGLE (AMD Radeon RX 6900 XT Direct3D11 vs_5_0)",
        # Intel GPUs
        "ANGLE (Intel(R) UHD Graphics Direct3D11 vs_5_0)",
        "ANGLE (Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0)",
        # Apple GPUs
        "Apple M1 Pro",
        "Apple M2 Pro",
        "Apple M3 Pro"
    ])
    
    # Generate consistent canvas and audio fingerprints with hardware-specific noise
    canvas_noise = f"{random.random()}_{time.time()}_{screen_dims[0]}_{webgl_renderer}"
    canvas_fingerprint = hashlib.sha256(canvas_noise.encode()).hexdigest()
    
    audio_noise = f"{random.random()}_{time.time()}_{hardware_concurrency}_{device_memory}"
    audio_fingerprint = hashlib.sha256(audio_noise.encode()).hexdigest()
    
    # Language and locale settings with realistic Italian preferences
    language_choices = [
        "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "it;q=0.9,en-US;q=0.8,en;q=0.7",
        "it-IT,it;q=0.9,en;q=0.8",
        "it-IT,it;q=0.9,en-GB;q=0.8,en;q=0.7",
        "it-IT,it;q=0.9,fr-FR;q=0.8,fr;q=0.7",
        "it-IT,it;q=0.9,de-DE;q=0.8,de;q=0.7",
        "it-IT,it;q=0.9,es-ES;q=0.8,es;q=0.7"
    ]
    
    # Time zone and location data specific to Italy
    timezone_choices = [
        "Europe/Rome",
        "Europe/Milan",
        "Europe/Vatican",
        "Europe/Paris",  # Some Italian users might use Paris timezone
        "Europe/Berlin", # Some Italian users might use Berlin timezone
        "Europe/Madrid"  # Some Italian users might use Madrid timezone
    ]
    
    # Additional browser-specific details
    browser_features = {
        "touch_support": random.choice([True, False]),
        "timezone_offset": random.randint(-120, 120),
        "do_not_track": random.choice([True, False]),
        "webgl_version": random.choice(["WebGL 1.0", "WebGL 2.0"]),
        "webgl_shading_language_version": random.choice(["WebGL GLSL ES 1.0", "WebGL GLSL ES 3.0"]),
        "max_touch_points": random.choice([0, 1, 2, 5, 10]),
        "hardware_acceleration": True,
        "webgl_vendor_unmasked": webgl_vendor,
        "webgl_renderer_unmasked": webgl_renderer,
        "webgl_debug_renderer_info": True,
        "webgl_debug_shaders": True,
        "webgl_debug_extensions": True
    }
    
    fingerprint = {
        "screen_width": screen_dims[0],
        "screen_height": screen_dims[1],
        "viewport_width": viewport_width,
        "viewport_height": viewport_height,
        "color_depth": color_depth,
        "pixel_depth": pixel_depth,
        "device_memory": device_memory,
        "hardware_concurrency": hardware_concurrency,
        "platform": platform,
        "platform_details": platform_details,
        "webgl_vendor": webgl_vendor,
        "webgl_renderer": webgl_renderer,
        "canvas_fingerprint": canvas_fingerprint,
        "audio_fingerprint": audio_fingerprint,
        "languages": random.choice(language_choices),
        **browser_features
    }
    
    return fingerprint

def generate_fingerprint_header():
    """Generate a fingerprint header for HTTP requests"""
    fingerprint = generate_browser_fingerprint()
    # Concatenate all fingerprint values into a single string
    fingerprint_str = (
        f"{fingerprint['screen_width']}x{fingerprint['screen_height']};"
        f"Lang:{fingerprint['languages']};"
        f"Canvas:{fingerprint['canvas_fingerprint']};"
        f"Audio:{fingerprint['audio_fingerprint']}"
    )
    # Hash the combined string to produce a fingerprint header value
    header_value = hashlib.sha256(fingerprint_str.encode('utf-8')).hexdigest()
    return {
        "X-Browser-Fingerprint": header_value,
        # "Sec-Ch-Ua-Platform": random.choice(['"Windows"', '"macOS"', '"Linux"']),
        #"Sec-Ch-Ua-Mobile": "?0",
        "Viewport-Width": str(fingerprint['screen_width']),
        "Viewport-Height": str(fingerprint['screen_height']),
        "Accept-Language": fingerprint['languages']
    }

class TLS_Scraper:

    @staticmethod
    def get_randomized_tls_client():
        """
        Returns a new TLS client session with a randomized client identifier.
        Uses secrets.choice for secure randomness.
        """
        # Map of Chrome versions to their corresponding user agents
        chrome_versions = {
            "chrome_120": chrome120_user_agents,
            "chrome_121": chrome121_user_agents,
            "chrome_122": chrome122_user_agents,
        }
        
        # Select a random Chrome version
        client_identifier = secrets.choice(list(chrome_versions.keys()))
        print(f"🔹 Using random TLS client identifier: {client_identifier}")
        
        # Get corresponding user agents for the selected version
        user_agents = chrome_versions[client_identifier]
        
        # Create a new TLS client session with minimal configuration
        client = tls_client.Session(
            client_identifier=client_identifier,
            random_tls_extension_order=True
        )

        user_agent = random.choice(user_agents)

        # Attempt to disable SSL verification if supported
        try:
            client.verify = False
        except Exception as error:
            print("⚠️ Error disabling SSL verification:", error)

        return client, user_agent

    def __init__(self):
        # Initialize with SSL verification disabled
        self.client, self.user_agent = TLS_Scraper.get_randomized_tls_client()
        print(f"🔹 User agent: {self.user_agent}")
        # Disable SSL verification if the library supports it
        try:
            # Not all versions of tls_client support this attribute directly
            self.client.verify = False
        except:
            pass

        # Configure proxy with authentication
        self.proxy_url = "brd.superproxy.io:33335"
        self.proxy_user = "brd-customer-hl_d7c58bf1-zone-testing"
        self.proxy_pass = "c09798vssihc"
        self.proxy_list = []
        # Initialize request history
        self.request_history = []
        self.csv_file = "request_history.csv"
        self._ensure_csv_exists()

        # Load user agents from JSON file (same as TrovaPrezziRequester)
        # user_agents_path = os.path.join(os.path.dirname(__file__), "user_agents.json")
        # with open(user_agents_path, encoding="utf-8") as f:
        #     self.user_agents = json.load(f)

        self.referers = ["https://www.trovaprezzi.it/"]

    def _ensure_csv_exists(self):
        """Ensure the CSV file exists with proper headers"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                import csv

                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "url",
                        "proxy",
                        "user_agent",
                        "status_code",
                        "retry_count",
                        "headers",
                        "response_length",
                    ]
                )

    def record_request(
        self, url, proxy, headers, status_code, retry_count, response_length
    ):
        """Record request details to CSV file"""
        try:
            with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
                import csv

                writer = csv.writer(f)
                writer.writerow(
                    [
                        datetime.now().isoformat(),
                        url,
                        proxy or "none",
                        headers.get("User-Agent", "unknown"),
                        status_code,
                        retry_count,
                        json.dumps(headers, ensure_ascii=False),
                        response_length,
                    ]
                )
        except Exception as e:
            print(f"⚠️ Error recording request to CSV: {str(e)}")

    def get_headers(self):
        accept_values = [
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        ]
        
        # Get base headers
        headers = {
            "User-Agent": self.user_agent,
            "Accept": random.choice(accept_values),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": random.choice(self.referers),
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "no-cache",
        }
        
        # Add fingerprint headers
        fingerprint_headers = generate_fingerprint_header()
        headers.update(fingerprint_headers)
        
        return headers

    def get_random_proxy(self, method="swiftshadow"):
        """
        Obtain a random proxy using the Swiftshadow library.
        """
        try:
            from swiftshadow import QuickProxy

            if method == "swiftshadow":
                proxy = QuickProxy()
            elif method == "proxybroker":
                proxy = random.choice(self.proxy_list)
            else:
                raise ValueError(f"Invalid proxy method: {method}")
            # If proxy is already a valid string, return it
            if isinstance(proxy, str):
                # Don't prepend http:// if it's already there
                if proxy.startswith("http://") or proxy.startswith("https://"):
                    return proxy
                else:
                    return "http://" + proxy
            else:
                # Parse the proxy object string representation.
                s = str(proxy)
                import re

                m_ip = re.search(r"ip='([^']+)'", s)
                m_protocol = re.search(r"protocol='([^']+)'", s)
                m_port = re.search(r"port=(\d+)", s)
                ip = m_ip.group(1) if m_ip else ""
                protocol = m_protocol.group(1) if m_protocol else "http"
                port = m_port.group(1) if m_port else ""
                if ip and port:
                    return f"{protocol}://{ip}:{port}"
                else:
                    print("Error: Unable to parse proxy information from Swiftshadow.")
                    return None
        except Exception as e:
            print(f"Error getting proxy from Swiftshadow: {e}")
            return None

    def clear_proxies(self):
        """Clear all proxies from the client"""
        self.client.proxies = {}
        print("Proxies cleared from TLS client")

    def clear_cache(self):
        """Clear cookies and cache from the client"""
        try:
            # Attempt to clear cookies - this may not be supported in all versions
            if hasattr(self.client, "cookies"):
                self.client.cookies.clear()
                print("Cookies cleared from TLS client")

            # Create a fresh session to ensure no caching
            self.client, self.user_agent = self.get_randomized_tls_client()
            try:
                self.client.verify = False
            except:
                pass

            print("TLS client session refreshed to clear cache")
        except Exception as e:
            print(f"Error when clearing cache: {str(e)}")

    def update_proxies_with_proxybroker(self, limit: int = 5) -> None:
        """
        Fetches free proxies from various sources and updates self.proxies_list.
        """
        try:
            proxies = []

            # Try different proxy sources
            proxy_sources = [
                # "https://api.proxyscrape.com/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            ]

            for source in proxy_sources:
                try:
                    print(f"Fetching proxies from: {source}")
                    response = requests.get(source, timeout=10)
                    if response.status_code == 200:
                        # Split response into lines and clean up
                        proxy_list = [
                            line.strip()
                            for line in response.text.splitlines()
                            if line.strip()
                        ]
                        # Add http:// prefix if not present
                        proxy_list = [
                            (
                                f"http://{proxy}"
                                if not proxy.startswith(("http://", "https://"))
                                else proxy
                            )
                            for proxy in proxy_list
                        ]
                        proxies.extend(proxy_list)
                        print(f"Found {len(proxy_list)} proxies from {source}")
                except Exception as e:
                    print(f"Error fetching from {source}: {str(e)}")
                    continue

            # Remove duplicates and limit the number of proxies
            proxies = list(set(proxies))[:limit]

            if proxies:
                self.proxy_list = proxies
                print(f"🔹 Successfully found {len(proxies)} unique proxies")
                print("Proxies found:", proxies)
            else:
                print("⚠️ No proxies found")

        except Exception as e:
            print(f"❌ Error updating proxies: {str(e)}")
            traceback.print_exc()
            # Keep the existing proxy list if update fails
            print("Keeping existing proxy list")

    def reset_client(self):
        """Reset the client completely - clearing proxies, cookies and cache"""
        self.clear_proxies()
        self.clear_cache()
        print("Client completely reset for fresh requests")

    def get_page(self, url, page_number=None, max_retries=100):
        """
        Get a page with retry mechanism for 403 statuses.

        Args:
            url: URL to fetch
            page_number: Optional page number for pagination
            max_retries: Maximum number of retries before giving up (default: 10)

        Returns:
            ScraperResponse object or None if failed
        """
        retries = 0
        last_response = None
        # self.update_proxies_with_proxybroker()
        while retries <= max_retries:
            if retries > 0:
                print(f"\n{'='*70}")
                print(f"🔄 RETRY ATTEMPT {retries}/{max_retries} FOR 403 FORBIDDEN")
                print(
                    f"🌐 TLS_Scraper: Changing proxy and clearing cache before retrying: {url}"
                )
                # Reset the client completely for a fresh attempt
                self.reset_client()
            else:
                print(f"\n{'='*70}")
                print(f"🌐 TLS_Scraper: Fetching page: {url}")

            # Set up proxies properly - get a new one for each retry
            try:
                # Get new proxy
                # if retries % 2 == 0:
                #     random_proxy = self.get_random_proxy(method="proxybroker")
                # else:
                #     random_proxy = self.get_random_proxy(method="swiftshadow")
                random_proxy = (
                    self.proxy_user + ":" + self.proxy_pass + "@" + self.proxy_url
                )
                print(f"Using proxy: {random_proxy}")
                if random_proxy:
                    # Fix: Make sure we're using the right proxy format
                    if random_proxy.startswith("http://") or random_proxy.startswith(
                        "https://"
                    ):
                        proxy_string = random_proxy
                    else:
                        proxy_string = f"https://{random_proxy}"

                    self.client.proxies = {
                        "http": proxy_string,
                        "https": proxy_string,
                    }
                    print(f"Using proxy: {proxy_string}")
                else:
                    print("⚠️ No proxy available, proceeding without proxy")
            except Exception as proxy_error:
                print(f"⚠️ Error setting up proxy: {proxy_error}")
                # Ensure we can still proceed without proxy
                self.clear_proxies()

            print(f"SSL verification disabled")

            # Get new headers for each retry
            headers = self.get_headers()
            # Add cache-control headers to prevent caching
            headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
            headers["Pragma"] = "no-cache"
            headers["Expires"] = "0"
            print(
                f"Using headers with cache prevention:\n{json.dumps(headers, indent=2)}"
            )

            try:
                # Try to make the request
                response = None

                # Method 1: TLS client (without timeout parameter)
                try:
                    print("Attempt 1: Using TLS client with proxy...")
                    # Remove the timeout parameter as it's not supported
                    response = self.client.get(url, headers=headers)
                    print(
                        f"✅ TLS client successful - Response status code: {response.status_code}"
                    )
                except Exception as tls_error:
                    print(f"⚠️ TLS client error: {str(tls_error)}")
                    print(f"Error type: {type(tls_error).__name__}")
                    response = None

                # Method 2: Requests with SSL verification disabled
                if response is None:
                    try:
                        print(
                            "Attempt 2: Using standard requests library with SSL verification disabled..."
                        )
                        requests_response = requests.get(
                            url, headers=headers, verify=False, timeout=30
                        )
                        print(
                            f"✅ Standard requests successful - Response status code: {requests_response.status_code}"
                        )

                        # Create a custom response object using the class defined above
                        response = CustomResponse(requests_response)
                    except Exception as requests_error:
                        print(f"⚠️ Standard requests error: {str(requests_error)}")
                        print(f"Error type: {type(requests_error).__name__}")
                        response = None

                # Method 3: TLS client without proxy
                if response is None:
                    try:
                        print("Attempt 3: Using TLS client without proxy...")
                        # Save current proxies
                        original_proxies = self.client.proxies
                        # Clear proxies
                        self.clear_proxies()
                        # Try request without proxy
                        direct_response = self.client.get(url, headers=headers)
                        print(
                            f"✅ Direct TLS request successful - Response status code: {direct_response.status_code}"
                        )
                        response = direct_response
                        # Restore original proxies
                        self.client.proxies = original_proxies
                    except Exception as direct_tls_error:
                        print(f"⚠️ Direct TLS request error: {str(direct_tls_error)}")
                        print(f"Error type: {type(direct_tls_error).__name__}")
                        # Restore original proxies
                        self.client.proxies = original_proxies
                        response = None

                # Method 4: Direct requests without proxy as last resort
                if response is None:
                    try:
                        print(
                            "Attempt 4: Using direct requests without proxy (last resort)..."
                        )
                        direct_response = requests.get(
                            url, headers=headers, verify=False, timeout=30
                        )
                        print(
                            f"✅ Direct request successful - Response status code: {direct_response.status_code}"
                        )

                        # Create a custom response object using the class defined above
                        response = CustomResponse(direct_response)
                    except Exception as direct_error:
                        print(f"⚠️ Direct request error: {str(direct_error)}")
                        print(f"Error type: {type(direct_error).__name__}")
                        response = None

                # If we have a response, process it
                if response:
                    # Check for 403 Forbidden status - if found, retry with a new proxy
                    if response.status_code == 403:
                        print(f"⚠️ RECEIVED 403 FORBIDDEN STATUS CODE")
                        print(
                            f"🔄 Will retry with a new proxy. Attempt {retries+1} of {max_retries}"
                        )
                        # Record the failed request
                        self.record_request(
                            url=url,
                            proxy=random_proxy,
                            headers=headers,
                            status_code=response.status_code,
                            retry_count=retries,
                            response_length=(
                                len(response.text) if hasattr(response, "text") else 0
                            ),
                        )
                        retries += 1
                        last_response = response
                        continue

                    # Get the response content safely - avoid using .text property directly
                    try:
                        # Correct way to get response text
                        response_text = response.content.decode(
                            "utf-8", errors="replace"
                        )
                        print(f"Response length: {len(response_text)} characters")
                        print(f"Response preview: {response_text[:200]}...")
                    except Exception as text_error:
                        print(f"Error getting response text: {str(text_error)}")
                        # Create an empty response as fallback
                        response_text = ""

                    # Check for CAPTCHA or blocking
                    if "captcha" in response_text.lower():
                        print("⚠️ CAPTCHA detected in response!")
                        # If captcha detected and we have retries left, try again with new proxy
                        if retries < max_retries:
                            print(
                                f"🔄 CAPTCHA detected - Will retry with a new proxy. Attempt {retries+1} of {max_retries}"
                            )
                            # Record the failed request
                            self.record_request(
                                url=url,
                                proxy=random_proxy,
                                headers=headers,
                                status_code=response.status_code,
                                retry_count=retries,
                                response_length=len(response_text),
                            )
                            retries += 1
                            last_response = response
                            continue

                    if (
                        "blocked" in response_text.lower()
                        or "banned" in response_text.lower()
                    ):
                        print("⚠️ IP possibly blocked!")
                        # If blocking detected and we have retries left, try again with new proxy
                        if retries < max_retries:
                            print(
                                f"🔄 IP BLOCKED - Will retry with a new proxy. Attempt {retries+1} of {max_retries}"
                            )
                            # Record the failed request
                            self.record_request(
                                url=url,
                                proxy=random_proxy,
                                headers=headers,
                                status_code=response.status_code,
                                retry_count=retries,
                                response_length=len(response_text),
                            )
                            retries += 1
                            last_response = response
                            continue

                    # Record successful request
                    self.record_request(
                        url=url,
                        proxy=random_proxy,
                        headers=headers,
                        status_code=response.status_code,
                        retry_count=retries,
                        response_length=len(response_text),
                    )

                    # Return a response-like object compatible with callbacks
                    if response.status_code == 200:
                        print("✅ SUCCESS: Got 200 OK response")
                        # Create a meta dict with page_number
                        meta = {"page_number": page_number} if page_number else {}

                        # Get headers safely
                        try:
                            headers_dict = response.headers
                        except Exception:
                            headers_dict = {}

                        # Create a Response-like object that matches what Scrapy would return
                        return ScraperResponse(
                            url=url,
                            text=response_text,
                            status=response.status_code,
                            meta=meta,
                            headers=headers_dict,
                        )
                    else:
                        print(f"⚠️ ERROR: Got status code {response.status_code}")
                        print(f"Response preview: {response_text[:500]}...")

                        # Return a response object even with error status so callback can handle it
                        return ScraperResponse(
                            url=url,
                            text=response_text,
                            status=response.status_code,
                            meta={"page_number": page_number} if page_number else {},
                            headers=getattr(response, "headers", {}),
                        )
                else:
                    # No response on this attempt
                    if retries < max_retries:
                        retries += 1
                        print(
                            f"🔄 No response received - Will retry with a new proxy. Attempt {retries} of {max_retries}"
                        )
                        continue
                    else:
                        print(
                            "⚠️ ERROR: All request methods failed, no response received after all retries"
                        )
                        return None

            except Exception as e:
                print(f"⚠️ Error fetching {url}: {str(e)}")
                print(f"Error type: {type(e).__name__}")
                print(traceback.format_exc())

                # If we still have retries left, try again
                if retries < max_retries:
                    retries += 1
                    print(
                        f"🔄 Exception occurred - Will retry with a new proxy. Attempt {retries} of {max_retries}"
                    )
                    continue
                return None

        # If we've exhausted all retries and still have a 403, return the last response
        if last_response and retries > max_retries:
            print(f"⚠️ Exhausted all {max_retries} retries for 403 status code")
            try:
                response_text = last_response.content.decode("utf-8", errors="replace")
                # Record the final failed request
                self.record_request(
                    url=url,
                    proxy=random_proxy,
                    headers=headers,
                    status_code=last_response.status_code,
                    retry_count=retries,
                    response_length=len(response_text),
                )
                return ScraperResponse(
                    url=url,
                    text=response_text,
                    status=last_response.status_code,
                    meta={"page_number": page_number} if page_number else {},
                    headers=getattr(last_response, "headers", {}),
                )
            except:
                return None

        return None


# Create a global instance
tls_scraper = TLS_Scraper()


# Legacy code below
class CustomRetryMiddleware(RetryMiddleware):
    EXCEPTIONS_TO_RETRY = (
        ConnectionLost,
        ConnectionDone,
        ConnectError,
        TimeoutError,
        ResponseFailed,
        scrapy.spidermiddlewares.httperror.HttpError,
    )

    def process_response(self, request, response, spider):
        spider.logger.info("=" * 70)
        spider.logger.info(f"Processing response for: {response.url}")
        spider.logger.info(f"Status: {response.status}")
        spider.logger.info(f"Headers: {dict(response.headers)}")

        # Log response content for non-200 responses
        if response.status != 200:
            spider.logger.warning("Non-200 response received!")
            try:
                content = response.text[:1000]  # First 1000 chars
                spider.logger.warning(f"Response content preview: {content}")
            except Exception as e:
                spider.logger.error(f"Could not read response content: {str(e)}")

        if response.status == 403 or response.status >= 500:
            spider.logger.warning(f"Got {response.status}, retrying {request.url}")
            spider.logger.warning(f"Request headers were: {request.headers}")
            spider.logger.warning(f"Request cookies were: {request.cookies}")
            return self._retry(request, response.status, spider) or response

        spider.logger.info("=" * 70)
        return response

    def process_exception(self, request, exception, spider):
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY):
            spider.logger.error("=" * 70)
            spider.logger.error(f"Connection error for {request.url}")
            spider.logger.error(f"Exception type: {type(exception).__name__}")
            spider.logger.error(f"Exception details: {str(exception)}")
            spider.logger.error(f"Request headers: {request.headers}")
            spider.logger.error(f"Request cookies: {request.cookies}")
            spider.logger.error("=" * 70)
            return self._retry(request, exception, spider)

    def _retry(self, request, reason, spider):
        retries = request.meta.get("retry_times", 0)
        if retries < spider.max_retries:
            retries += 1
            request.meta["retry_times"] = retries

            delay = spider.retry_delay * (2 ** (retries - 1))
            spider.logger.info(
                f"Waiting {delay:.2f} seconds before retry {retries} for {request.url}"
            )

            def _get_new_request():
                new_headers = spider.get_random_headers()
                spider.logger.debug(f"New headers for retry: {new_headers}")
                new_request = request.replace(
                    headers=new_headers, cookies={}, dont_filter=True, meta=request.meta
                )
                # Optional: rotate proxy if available
                if hasattr(spider, "get_random_proxy"):
                    new_proxy = spider.get_random_proxy()
                    if new_proxy:
                        new_request.meta["proxy"] = new_proxy
                        spider.logger.debug(f"Using new proxy: {new_proxy}")
                return new_request

            # Use deferLater for a non-blocking delay
            return deferLater(
                spider.crawler.engine.downloader.slots.get(request).reactor,
                delay,
                _get_new_request,
            )
        spider.logger.error(f"Max retries reached for {request.url}")
        return None


class TrovaPrezziRequester(Spider):
    name = "trovaprezzi_requester"

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            __name__ + ".CustomRetryMiddleware": 550,
        },
        "DOWNLOAD_DELAY": random.uniform(0.5, 1),  # Increased delay
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 1,
        "COOKIES_ENABLED": False,
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "DEBUG",
        "HTTPERROR_ALLOW_ALL": True,
        "HTTPERROR_ALLOWED_CODES": [403, 404, 410, 500, 502, 503],
        "DOWNLOAD_TIMEOUT": 30,  # Increased timeout
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 8,  # Increased retries
        "DUPEFILTER_CLASS": "scrapy.dupefilters.BaseDupeFilter",
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy.core.downloader.handlers.http2.H2DownloadHandler",
        },
    }

    def __init__(self, *args, **kwargs):
        super(TrovaPrezziRequester, self).__init__(*args, **kwargs)

        # Load user agents
        # user_agents_path = os.path.join(os.path.dirname(__file__), "user_agents.json")
        # with open(user_agents_path, encoding="utf-8") as f:
        #     self.user_agents = json.load(f)

        self.max_retries = 8
        self.retry_delay = 15
        self.referers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.trovaprezzi.it/",
            "https://www.yahoo.com/",
            "https://duckduckgo.com/",
        ]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(TrovaPrezziRequester, cls).from_crawler(crawler, *args, **kwargs)
        spider.callback = kwargs.get("callback")
        spider.start_urls = [kwargs.get("url")] if kwargs.get("url") else []
        return spider

    def get_random_headers(self):
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",  # Changed to same-origin
            "Sec-Fetch-User": "?1",
            "Pragma": "no-cache",
            "DNT": "1",
            "Referer": random.choice(self.referers),
        }

    def start_requests(self):
        self.logger.info("Starting requests with URLs: %s", self.start_urls)
        for url in self.start_urls:
            self.logger.info("Making request to: %s", url)
            headers = self.get_random_headers()
            self.logger.debug("Using headers: %s", headers)
            yield Request(
                url,
                callback=self.parse,
                headers=headers,
                meta={
                    "dont_retry": False,
                    "retry_times": 0,
                    "handle_httpstatus_all": True,
                    "download_timeout": 30,
                },
                dont_filter=True,
                cookies={},
            )

    def parse(self, response):
        self.logger.info("=" * 70)
        self.logger.info(f"Response received for: {response.url}")
        self.logger.info(f"Response status: {response.status}")
        self.logger.info(f"Response headers: {dict(response.headers)}")

        # Log response details
        try:
            if response.status != 200:
                self.logger.warning("Non-200 status code received")
                self.logger.warning(f"Response body preview: {response.text[:1000]}")

                # Check for common error indicators
                if "captcha" in response.text.lower():
                    self.logger.error("CAPTCHA detected in response!")
                if "rate limit" in response.text.lower():
                    self.logger.error("Rate limiting message detected!")
                if "blocked" in response.text.lower():
                    self.logger.error("IP blocking message detected!")

            self.logger.info(
                f"Content type: {response.headers.get('Content-Type', b'').decode()}"
            )
            self.logger.info(f"Content length: {len(response.body)}")

        except Exception as e:
            self.logger.error(f"Error processing response: {str(e)}")

        self.logger.info("=" * 70)

        if hasattr(self, "callback") and self.callback:
            self.logger.info("Calling external callback")
            try:
                result = self.callback(response)
                self.logger.info("External callback completed successfully")
                return result
            except Exception as e:
                self.logger.error(f"Error in external callback: {str(e)}")
                self.logger.error(f"Callback error traceback:", exc_info=True)
                raise
        return response


def get_page_content(
    url,
    venditore,
    categoria=None,
    page_number=None,
    callback=None,
    is_first_request=True,
    max_retries=100,
):
    """
    Function to get a page content using TLS client or Scrapy

    Args:
        url: URL to scrape
        venditore: Vendor name
        categoria: Category name (optional)
        page_number: Page number (optional)
        callback: Callback function to process response (optional)
        is_first_request: Whether this is the first request in a sequence (optional)
        max_retries: Maximum number of retries for 403 errors (default 10)

    Returns:
        bool: Success status
    """
    log_prefix = f"[{venditore}]"
    if categoria:
        log_prefix += f"[{categoria}]"
    if page_number:
        log_prefix += f"[Page {page_number}]"

    print("\n" + "=" * 70)
    print(f"{log_prefix} STARTING SCRAPE | URL: {url}")
    print(f"{log_prefix} Using max_retries={max_retries} for 403 errors")

    # Use the TLS client approach instead of Scrapy
    try:
        # Get the page using TLS client
        response = tls_scraper.get_page(url, page_number, max_retries=max_retries)

        if response:
            # Print response summary with highlighted status code
            print("\n" + "=" * 50)
            print(f"{log_prefix} RESPONSE SUMMARY:")

            # Highlight status code with color or formatting
            status_text = f"STATUS CODE: {response.status}"
            if response.status == 200:
                status_text = f"✅ {status_text} (OK)"
            else:
                status_text = f"⚠️ {status_text} (Error)"
            print(status_text)

            print(f"URL: {response.url}")

            if hasattr(response, "headers") and response.headers:
                try:
                    content_type = response.headers.get("Content-Type", "")
                    if isinstance(content_type, bytes):
                        content_type = content_type.decode("utf-8", errors="ignore")
                    print(f"CONTENT TYPE: {content_type}")
                except:
                    pass

            content_size = (
                len(response.body)
                if hasattr(response, "body")
                else len(response.text.encode("utf-8"))
            )
            print(f"CONTENT SIZE: {content_size} bytes")

            # Print a preview for non-200 responses
            if response.status != 200:
                preview = response.text[:500].replace("\n", " ").replace("\r", "")
                print(f"RESPONSE PREVIEW: {preview}...")
            print("=" * 50)

            # Call the callback if provided
            if callback:
                print(f"{log_prefix} Calling callback function with response")
                try:
                    result = callback(response)
                    print(f"{log_prefix} Callback completed successfully")
                    return True
                except Exception as e:
                    print(f"{log_prefix} ⚠️ ERROR IN CALLBACK: {str(e)}")
                    traceback.print_exc()
                    return False
            else:
                return True
        else:
            print(f"{log_prefix} ❌ FAILED TO FETCH PAGE: No response received")

            # Print a failure summary
            print("\n" + "=" * 50)
            print(f"{log_prefix} REQUEST FAILED")
            print(f"STATUS CODE: Unknown (No response)")
            print(f"URL: {url}")
            print("=" * 50)
            return False

    except Exception as e:
        print(f"{log_prefix} ❌ ERROR MAKING REQUEST: {str(e)}")
        print(f"ERROR TYPE: {type(e).__name__}")
        traceback.print_exc()

        # Print an error summary
        print("\n" + "=" * 50)
        print(f"{log_prefix} REQUEST ERROR")
        print(f"ERROR TYPE: {type(e).__name__}")
        print(f"ERROR MESSAGE: {str(e)}")
        print(f"URL: {url}")
        print("=" * 50)
        return False
