from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import pandas as pd
import random
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class AmazonScraper:
    def __init__(self, proxy_api_key):
        self.base_url = "https://www.amazon.com/s?k={query}&page={page}"
        self.results = []
        self.proxy_api_key = proxy_api_key
        ua = UserAgent()
        options = webdriver.ChromeOptions()
        options.add_argument(f"user-agent={ua.random}")
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(
            service=Service(
                r"C:\chromedriver\chromedriver.exe"),
            options=options,
        )
        self.wait = WebDriverWait(self.driver, 10)

    def fetch_page(self, query, page):
        url = self.base_url.format(query=query, page=page)
        proxy_url = f"https://api.scraperapi.com?api_key={self.proxy_api_key}&url={url}"
        try:
            self.driver.get(proxy_url)
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "s-main-slot")))
            time.sleep(random.uniform(3, 7))  # Adjusted sleep time
            return self.driver.page_source
        except Exception as e:
            print(f"Failed to fetch page {page}. Error: {e}")
            return None

    def extract_item_details(self, soup):
        items = []
        for item in soup.find_all("div", {"data-component-type": "s-search-result"}):
            try:
                title = item.h2.text.strip() if item.h2 else "No title"

                # Extract and convert price
                pricew = item.find("span", {"class": "a-price-whole"})
                pricef = item.find("span", {"class": "a-price-fraction"})
                if pricew:
                    price = float(pricew.text.strip().replace(",", ""))
                    if pricef:
                        price += float(f"0.{pricef.text.strip()}")
                else:
                    price = float('inf')  # Assign a high value for missing prices to sort them last

                # Extract and convert rating
                rating = item.find("span", {"class": "a-icon-alt"})
                rating = float(rating.text.split()[0]) if rating else 0.0

                # Extract reviews
                reviews = item.find("span", {"class": "a-size-base"})
                reviews = int(reviews.text.replace(",", "")) if reviews and reviews.text.replace(",",
                                                                                                 "").isdigit() else 0

                # Extract URLs
                url = (
                    "https://www.amazon.com"
                    + item.find("a", {"class": "a-link-normal"})["href"]
                    if item.find("a", {"class": "a-link-normal"})
                    else "URL not available"
                )
                image_url = (
                    item.find("img", {"class": "s-image"})["src"]
                    if item.find("img", {"class": "s-image"})
                    else "No image"
                )

                items.append({
                    "Name": title,
                    "Price": price,  # Ensure numeric
                    "Rating": rating,  # Ensure numeric
                    "Reviews": reviews,
                    "ImageURL": image_url,
                    "URL": url,
                })
            except (AttributeError, ValueError) as e:
                print(f"Error extracting item details: {e}")
        return items

    def scrape(self, query, pages=1):
        for page in range(1, pages + 1):
            print(f"Scraping page {page}...")
            html = self.fetch_page(query, page)
            if not html:
                print(f"Failed to retrieve page {page}. Skipping.")
                continue

            soup = BeautifulSoup(html, "html.parser")
            items = self.extract_item_details(soup)
            self.results.extend(items)

    def filter_and_sort_items(self, sort_by="Price", order="low_to_high"):
        if sort_by == "Price":
            fn = lambda x: x["Price"]
        elif sort_by == "Rating":
            fn = lambda x: x["Rating"]
        else:
            return self.results

        reverse = order == "high_to_low"
        self.results = sorted(self.results, key=fn, reverse=reverse)

    def save_results(self):
        df = pd.DataFrame(self.results)
        filename = "amazon_scraper"
        df.to_csv(f"{filename}.csv", index=False)
        print("Filtered and sorted results saved to amazon_scraper.csv")

        df.to_excel(f"{filename}.xlsx", index=False)
        print("Filtered and sorted results saved to amazon_scraper.xlsx")

        with open(f"{filename}.json", 'w') as file:
            json.dump(self.results, file, indent=4)
        print("Filtered and sorted results saved to amazon_scraper.json")

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    proxy_api_key = "c34a45641019805866c9db9049ea4abd"
    scraper = AmazonScraper(proxy_api_key)
    try:
        search_query = input("Enter a item name to search: ").replace(" ", "+")
        pages = int(input("Enter the number of pages to scrape: "))

        scraper.scrape(query=search_query, pages=pages)

        sort_by = input("Sort by (Price/Rating): ").capitalize()
        if sort_by not in ["Price", "Rating"]:
            print("Invalid input for sorting! Defaulting to Price.")
            sort_by = "Price"

        order = input("Order (low_to_high/high_to_low): ").lower()
        if order not in ["low_to_high", "high_to_low"]:
            print("Invalid order! Defaulting to low_to_high.")
            order = "low_to_high"

        scraper.filter_and_sort_items(sort_by=sort_by,
 order=order)
        scraper.save_results()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        scraper.close()

