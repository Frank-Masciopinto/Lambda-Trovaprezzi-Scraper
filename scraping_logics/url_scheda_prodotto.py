from bs4 import BeautifulSoup
import os
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import traceback
import time
import random
import asyncio
import aiohttp
from typing import List, Dict, Any
import os
from .request_handler import get_page_content, tls_scraper

BASE_API_URL = os.environ.get("BASE_API_URL", "http://172.17.0.1:8000")
print(f"BASE_API_URL: {BASE_API_URL}")
# Try both import styles to ensure compatibility


class SchedaProdottoScraper:
    def __init__(self, titolo_prodotto, categoria_id=None, scheda_prodotto=None):
        self.titolo_prodotto = titolo_prodotto
        self.categoria_id = categoria_id
        self.scheda_prodotto = scheda_prodotto
        self.url = self.get_start_url()
        self.products = []
        self.total_products = 0
        self.pages_scraped = 0

    def get_start_url(self):
        if self.categoria_id == "1":
            self.categoria_id = "-1"
        return f"https://www.trovaprezzi.it/categoria.aspx?id={-1}&libera={self.titolo_prodotto}"

    def cerca_scheda_prodotto_estrai_dati_competitor(self):
        """Estrae prezzi e venditori con una sola richiesta HTTP, gestendo le varianti di prodotto"""
        prezzi = []
        venditori = []
        url = self.url
        url_utilizzato = url
        competitors = []
        print(f"Inizio scraping URL: {url}")

        try:
            import re
            from urllib.parse import urlparse

            # Use get_page_content instead of direct requests
            response = get_page_content(url, "trovaprezzi", callback=lambda r: r)
            print("V ->> returned response", response)
            if not response:
                print("Failed to get page content")
                return "Failed to get page content", False

            # Get the final URL from response
            final_url = response.url
            if final_url != url:
                print(f"Reindirizzamento rilevato: {url} → {final_url}")
                url_utilizzato = final_url

            if response.status != 200:
                print(f"Errore nella richiesta: {response.status}")
                return "Errore nella richiesta", False

            soup = BeautifulSoup(response.text, "html.parser")

            # Verifica se siamo in una pagina con varianti
            variations_container = soup.select_one("div.variations_container")
            if variations_container and self.titolo_prodotto:
                print(f"Pagina con varianti rilevata per '{self.titolo_prodotto}'")

                # Estrai codici modello dal nome del prodotto (come 9B9R8EA nell'esempio)
                model_matches = re.findall(
                    r"[A-Z0-9]{5,}(?:\-[A-Z0-9]+)?", self.titolo_prodotto
                )
                model_numbers = [m.strip() for m in model_matches]
                print(f"Codici modello estratti: {model_numbers}")

                # Modifica il metodo di selezione delle varianti
                variants = variations_container.select("a.variation")
                if not variants:
                    variants = variations_container.select("div.slick-slide a")
                if not variants:
                    variants = variations_container.select("div.variation a")
                if not variants:
                    # Ultima chance: qualsiasi link nella container delle varianti
                    variants = variations_container.select("a[href]")

                print(f"Trovati {len(variants)} link di varianti")

                # Analizza ogni link di variante
                best_match = None
                best_score = -1
                best_url = None

                for variant in variants:
                    variant_url = variant.get("href")
                    # Ottieni il testo o il titolo della variante
                    variant_title = variant.get("title") or variant.text.strip()

                    # Debug per vedere tutte le varianti disponibili
                    print(f"Variante disponibile: {variant_title} → {variant_url}")

                    if not variant_url or not variant_title:
                        continue

                    # Calcola punteggio di corrispondenza
                    score = 0

                    # Bonus maggiore per corrispondenza esatta di codice modello
                    for model in model_numbers:
                        if (
                            model.lower() in variant_title.lower()
                            or model.lower() in variant_url.lower()
                        ):
                            score += 10
                            print(
                                f"Match di codice modello '{model}' in variante '{variant_title}'"
                            )

                    # Conta quante parole chiave corrispondono
                    keywords = re.sub(
                        r"[^\w\s]", " ", self.titolo_prodotto.lower()
                    ).split()
                    keyword_matches = sum(
                        1 for keyword in keywords if keyword in variant_title.lower()
                    )
                    score += keyword_matches

                    # Bonus per variante attualmente selezionata
                    if (
                        "active" in variant.get("class", [])
                        or variant.parent
                        and "active" in variant.parent.get("class", [])
                    ):
                        score += 0.5

                    print(f"Variante: '{variant_title}' - Score: {score}")

                    # Aggiorna la migliore corrispondenza
                    if score > best_score:
                        best_score = score
                        best_match = variant_title
                        best_url = variant_url

                # Se abbiamo trovato una variante migliore, usa quell'URL
                if best_url and best_score > 0:
                    print(
                        f"→ Selezionata variante: '{best_match}' (score {best_score})"
                    )

                    # Converti URL relativo in assoluto se necessario
                    if best_url.startswith("/"):
                        parsed_url = urlparse(final_url)  # Usa final_url, non url
                        best_url = (
                            f"{parsed_url.scheme}://{parsed_url.netloc}{best_url}"
                        )

                    print(f"→ Nuovo URL variante completo: {best_url}")
                    url_utilizzato = best_url

                    # Nuova richiesta per la variante specifica
                    time.sleep(random.uniform(1, 2))
                    response = get_page_content(
                        best_url, "trovaprezzi", callback=lambda r: r
                    )
                    if response.status == 200:
                        soup = BeautifulSoup(response.text, "html.parser")
                        print("Caricata pagina della variante con successo")
                    else:
                        logging.warning(
                            f"Errore accedendo alla variante: {response.status}"
                        )

            # Estrazione prezzi
            elementi_prezzo = soup.select("div.item_total_price")
            elementi_venditore = soup.select("div.merchant_name_and_logo")

            for prezzo, venditore in zip(elementi_prezzo, elementi_venditore):
                try:
                    prezzo_text = (
                        prezzo.text.strip()
                        .replace("€", "")
                        .replace("Tot", "")
                        .replace(".", "")
                        .replace(",", ".")
                        .strip()
                    )
                    venditore_text = venditore.select_one("a")["href"].split("/")[-1]
                    competitors.append(
                        {"prezzo": float(prezzo_text), "venditore": venditore_text}
                    )
                except Exception as e:
                    print(f"Errore nel parsing del prezzo: {e}")
                    continue

            # Estrazione venditori
            print(f"Trovati {len(competitors)} competitors")

            # Aggiungere questo codice dopo l'estrazione dei venditori ma prima del salvataggio nella cache
            # Intorno alla riga 335-340 della funzione estrai_dati_pagina

            # Verifica se abbiamo trovato meno di 4 risultati, prova con i suggerimenti
            if len(prezzi) < 4 or len(venditori) < 4:
                print(
                    f"Trovati solo {len(prezzi)} prezzi e {len(venditori)} venditori - Cerco nei suggerimenti"
                )

                # Cerca suggerimenti nella sidebar
                suggestions = (
                    soup.select("section.search_suggestions a.suggested_product")
                    or soup.select("div.desktop_sidebar a.suggested_product")
                    or soup.select("a.suggested_product.variant_with_versione")
                    or soup.select("div.related_products a[href]")
                )

                if suggestions:
                    print(f"Trovati {len(suggestions)} prodotti suggeriti")

                    best_suggestion = None
                    best_suggestion_score = -1
                    best_suggestion_url = None
                    best_suggestion_title = None

                    for suggestion in suggestions:
                        suggestion_url = suggestion.get("href")
                        suggestion_title = (
                            suggestion.get("title") or suggestion.text.strip()
                        )

                        # Skip se mancano informazioni essenziali
                        if not suggestion_url or not suggestion_title:
                            continue

                        # Debug
                        print(f"Suggerimento: '{suggestion_title}' → {suggestion_url}")

                        # Calcola punteggio di corrispondenza, simile alle varianti
                        score = 0

                        # Se c'è un codice modello, verifica corrispondenza
                        if self.titolo_prodotto:
                            model_matches = re.findall(
                                r"[A-Z0-9]{5,}(?:\-[A-Z0-9]+)?", self.titolo_prodotto
                            )
                            for model in model_matches:
                                if (
                                    model.lower() in suggestion_title.lower()
                                    or model.lower() in suggestion_url.lower()
                                ):
                                    score += 10
                                    print(
                                        f"Match di codice modello '{model}' in suggerimento '{suggestion_title}'"
                                    )

                            # Conta parole chiave corrispondenti
                            keywords = re.sub(
                                r"[^\w\s]", " ", self.titolo_prodotto.lower()
                            ).split()
                            keyword_matches = sum(
                                1
                                for keyword in keywords
                                if keyword in suggestion_title.lower()
                            )
                            score += keyword_matches

                        print(f"Suggerimento: '{suggestion_title}' - Score: {score}")

                        # Aggiorna miglior suggerimento
                        if score > best_suggestion_score:
                            best_suggestion_score = score
                            best_suggestion = suggestion
                            best_suggestion_url = suggestion_url
                            best_suggestion_title = suggestion_title

                    # Se troviamo un buon suggerimento, fai una nuova richiesta
                    if best_suggestion_url and best_suggestion_score > 0:
                        print(
                            f"→ Selezionato suggerimento: '{best_suggestion_title}' (score {best_suggestion_score})"
                        )

                        # Converti URL relativo in assoluto se necessario
                        if best_suggestion_url.startswith("/"):
                            parsed_url = urlparse(final_url)
                            best_suggestion_url = f"{parsed_url.scheme}://{parsed_url.netloc}{best_suggestion_url}"

                        print(f"→ Nuovo URL suggerimento: {best_suggestion_url}")

                        # Nuova richiesta per il prodotto suggerito
                        suggestion_response = get_page_content(
                            best_suggestion_url, "trovaprezzi", callback=lambda r: r
                        )

                        if suggestion_response.status == 200:
                            suggestion_soup = BeautifulSoup(
                                suggestion_response.text, "html.parser"
                            )
                            print("Caricata pagina del prodotto suggerito con successo")

                            # Estrai prezzi e venditori aggiuntivi
                            suggestion_prezzi = []
                            suggestion_venditori = []

                            # Estrazione prezzi dal suggerimento
                            suggestion_elementi_prezzo = suggestion_soup.select(
                                "div.item_total_price"
                            )
                    
                            # Estrazione venditori dal suggerimento
                            suggestion_elementi_venditore = suggestion_soup.select(
                                "div.merchant_name_and_logo"
                            )
                            for prezzo, venditore in zip(
                                suggestion_elementi_prezzo, suggestion_elementi_venditore
                            ):
                                try:
                                    prezzo_text = (
                                        prezzo.text.strip()
                                        .replace("€", "")
                                        .replace("Tot", "")
                                        .replace(".", "")
                                        .replace(",", ".")
                                        .strip()
                                    )
                                    venditore_text = venditore.select_one("a")[
                                        "href"
                                    ].split("/")[-1]
                                    competitors.append(
                                        {
                                            "prezzo": float(prezzo_text),
                                            "venditore": venditore_text,
                                        }
                                    )
                                except Exception as e:
                                    print(f"Errore nel parsing del prezzo: {e}")
                                    continue

                            print(
                                f"Trovati {len(suggestion_prezzi)} prezzi aggiuntivi e {len(suggestion_venditori)} venditori aggiuntivi"
                            )

                            # Ricorda l'URL utilizzato
                            if suggestion_prezzi or suggestion_venditori:
                                url_utilizzato = best_suggestion_url

                                print(
                                    f"Risultati combinati: {len(prezzi)} prezzi, {len(venditori)} venditori"
                                )
                        else:
                            logging.warning(
                                f"Errore accedendo al suggerimento: {suggestion_response.status}"
                            )

            # Salva nella cache
            print(f"Primi 10 competitors estratti: {competitors[:10]}")
            print(f"URL utilizzato per scraping: {url_utilizzato}")
            return competitors[:10], url_utilizzato

        except Exception as e:
            print(f"Errore: {e}")
            return e, False

    def estrai_dati_competitor(self):
        """Estrae prezzi e venditori con una sola richiesta HTTP, gestendo le varianti di prodotto"""
        prezzi = []
        venditori = []
        url = self.url
        url_utilizzato = url
        competitors = []
        print(f"Inizio scraping URL: {url}")

        try:
            import re
            from urllib.parse import urlparse

            # Use get_page_content instead of direct requests
            response = get_page_content(url, "trovaprezzi", callback=lambda r: r)
            print("V ->> returned response", response)
            if not response:
                print("Failed to get page content")
                return "Failed to get page content", False

            # Get the final URL from response
            final_url = response.url
            if final_url != url:
                print(f"Reindirizzamento rilevato: {url} → {final_url}")
                url_utilizzato = final_url

            if not str(response.status).startswith('2'):
                print(f"Errore nella richiesta: {response.status}")
                return "Errore nella richiesta", False

            soup = BeautifulSoup(response.text, "html.parser")

            # Estrazione prezzi
            elementi_prezzo = soup.select("div.item_total_price")
            elementi_venditore = soup.select("div.merchant_name_and_logo")

            for prezzo, venditore in zip(elementi_prezzo, elementi_venditore):
                try:
                    prezzo_text = (
                        prezzo.text.strip()
                        .replace("€", "")
                        .replace("Tot", "")
                        .replace(".", "")
                        .replace(",", ".")
                        .strip()
                    )
                    venditore_text = venditore.select_one("a")["href"].split("/")[-1]
                    competitors.append(
                        {"prezzo": float(prezzo_text), "venditore": venditore_text}
                    )
                except Exception as e:
                    print(f"Errore nel parsing del prezzo: {e}")
                    continue

            # Estrazione venditori
            print(f"Trovati {len(competitors)} competitors")

            # Aggiungere questo codice dopo l'estrazione dei venditori ma prima del salvataggio nella cache
            # Intorno alla riga 335-340 della funzione estrai_dati_pagina
            print(f"Primi 10 competitors estratti: {competitors[:10]}")
            print(f"URL utilizzato per scraping: {url_utilizzato}")
            return competitors[:10], url_utilizzato

        except Exception as e:
            print(f"Errore: {e}")
            return e, False