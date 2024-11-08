import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import pandas as pd
import redis
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from matplotlib import pyplot as plt

USERNAME = "xxx"
PASSWORD = "xxx"

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

CHROME_OPTIONS = Options()
# CHROME_OPTIONS.add_argument("--headless")  # Uncomment to run in headless mode
CHROME_OPTIONS.add_argument("--no-sandbox")
CHROME_OPTIONS.add_argument("--disable-dev-shm-usage")

class LinkedInPostAnalyzer:
    def __init__(self):
        try:
            self.driver = webdriver.Chrome(options=CHROME_OPTIONS)
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            raise
        try:
            self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        except Exception as e:
            print(f"Error connecting to Redis: {e}")
            raise
        self.post_data = []

    def login(self):
        
        self.driver.get("https://www.linkedin.com/login")
        username_field = self.driver.find_element(By.ID, "username")
        password_field = self.driver.find_element(By.ID, "password")
        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.ID, "global-nav"))
        )
        print("Login successful")
        

    def scrape_post_data(self, url: str) -> Dict:
        try:
            self.driver.get(url)
        # Increase the timeout if necessary
            WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "feed-shared-update-v2"))
            )
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            post_text = self.get_post_text(soup)
            media_link, media_type = self.get_media_info(soup)
            post_date = self.get_post_date(soup)
            post_reactions = self.get_post_reactions(soup)
            post_comments = self.get_post_comments(soup)
            post_shares = self.get_post_shares(soup)

        # Extract new URLs from the post content
            new_urls = self.extract_new_urls(soup)
            self.push_urls_to_queue(new_urls)

            return {
                "Post Text": post_text,
                "Media Link": media_link,
                "Media Type": media_type,
                "Post Date": post_date,
                "Likes": post_reactions,
                "Comments": post_comments,
                "Shares": post_shares,
            }
        except Exception as e:
            print(f"Error scraping data from {url}: {e}")
            return {}

    def extract_new_urls(self, soup: BeautifulSoup) -> List[str]:
        new_urls = []
        for link in soup.find_all("a", href=True):
            url = link["href"]
            if "linkedin.com/in/" in url or "linkedin.com/company/" in url:
                new_urls.append(url)
        return list(set(new_urls))

    def push_urls_to_queue(self, urls: List[str]):
        for url in urls:
            self.redis_client.rpush("linkedin_urls", url)

    def get_post_text(self, soup: BeautifulSoup) -> str:
        post_text_element = soup.find("div", {"class": "feed-shared-update-v2__description-wrapper"})
        return post_text_element.text.strip() if post_text_element else ""

    def get_media_info(self, soup: BeautifulSoup) -> Tuple[str, str]:
        media_info = [
            ("div", {"class": "update-components-video"}, "Video"),
            ("div", {"class": "update-components-linkedin-video"}, "Video"),
            ("div", {"class": "update-components-image"}, "Image"),
            ("article", {"class": "update-components-article"}, "Article"),
            ("div", {"class": "feed-shared-external-video__meta"}, "Youtube Video"),
            ("div", {"class": "feed-shared-mini-update-v2 feed-shared-update-v2__update-content-wrapper artdeco-card"}, "Shared Post"),
            ("div", {"class": "feed-shared-poll ember-view"}, "Other: Poll, Shared Post, etc"),
        ]

        for selector, attrs, media_type in media_info:
            element = soup.find(selector, attrs)
            if element:
                link = element.find("a", href=True)
                return link["href"] if link else "None", media_type
        return "None", "Unknown"

    def get_post_date(self, soup: BeautifulSoup) -> str:
        date_element = soup.find("div", {"class": "ml4 mt2 text-body-xsmall t-black--light"})
        if date_element:
            date_str = date_element.text.strip()
            return self.get_actual_date(date_str)
        return "0000-00-00"

    def get_actual_date(self, date_str: str) -> str:
        today = datetime.today()
        current_year = today.year

        if "hour" in date_str:
            return today.strftime("%Y-%m-%d")
        elif "day" in date_str:
            days = int(date_str.split(" ")[0])
            return (today - timedelta(days=days)).strftime("%Y-%m-%d")
        elif "week" in date_str:
            weeks = int(date_str.split(" ")[0])
            return (today - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
        elif "month" in date_str:
            months = int(date_str.split(" ")[0])
            return (today - timedelta(days=30*months)).strftime("%Y-%m-%d")
        elif "year" in date_str:
            years = int(date_str.split(" ")[0])
            return (today - timedelta(days=365*years)).strftime("%Y-%m-%d")
        else:
            split_date = date_str.split("-")
            if len(split_date) == 2:
                past_month = split_date[0].zfill(2)
                past_day = split_date[1].zfill(2)
                return f"{current_year}-{past_month}-{past_day}"
            elif len(split_date) == 3:
                past_month = split_date[0].zfill(2)
                past_day = split_date[1].zfill(2)
                past_year = split_date[2]
                return f"{past_year}-{past_month}-{past_day}"

    def get_post_reactions(self, soup: BeautifulSoup) -> int:
        reactions_element = soup.find_all(
        lambda tag: tag.name == "button" and "aria-label" in tag.attrs and "reaction" in tag["aria-label"].lower()
        )
        reactions_idx = 1 if len(reactions_element) > 1 else 0
        if reactions_element and reactions_element[reactions_idx].text.strip() != "":
            reactions_text = reactions_element[reactions_idx].text.strip().replace(',', '')
            return int(reactions_text)
        return 0
    
    def get_post_comments(self, soup: BeautifulSoup) -> int:
        comment_element = soup.find_all(
            lambda tag: tag.name == "button" and "aria-label" in tag.attrs and "comment" in tag["aria-label"].lower()
        )
        comment_idx = 1 if len(comment_element) > 1 else 0
        if comment_element and comment_element[comment_idx].text.strip() != "":
            comments_text = comment_element[comment_idx].text.strip().replace(',', '')
            return int(comments_text)
        return 0
    
    def get_post_shares(self, soup: BeautifulSoup) -> int:
        shares_element = soup.find_all(
            lambda tag: tag.name == "button" and "aria-label" in tag.attrs and "repost" in tag["aria-label"].lower()
        )
        shares_idx = 1 if len(shares_element) > 1 else 0
        if shares_element and shares_element[shares_idx].text.strip() != "":
            shares_text = shares_element[shares_idx].text.strip().replace(',', '')
            return int(shares_text)
        return 0

    def process_post_data(self):
        while True:
            url = self.redis_client.lpop("linkedin_urls")
            if not url:
                break
            url = url.decode("utf-8")
            post_data = self.scrape_post_data(url)
            if post_data:
                self.post_data.append(post_data)
                df = pd.DataFrame(self.post_data)
                print(df.columns)
                print(f"Processed post from URL: {url}")

    def calculate_metrics(self):
        if not self.post_data:
            print("No post data available to calculate metrics.")
            return {}

        df = pd.DataFrame(self.post_data)

        if "Post Date" not in df.columns:
            print("Post Date column is missing in the DataFrame.")
            return {}

        df['Post Date'] = pd.to_datetime(df['Post Date'], errors='coerce')
        monthly_posts = df['Post Date'].dt.to_period('M').value_counts().sort_index()
        avg_monthly_posts = monthly_posts.mean()

        avg_post_length = df["Post Text"].str.len().mean()

        media_posts = df[df["Media Type"] != "Unknown"]
        avg_likes_media = media_posts["Likes"].mean()

        avg_comments_media = media_posts["Comments"].mean()

        likes_dist = df["Likes"].value_counts(normalize=True).sort_index()
        comments_dist = df["Comments"].value_counts(normalize=True).sort_index()
        shares_dist = df["Shares"].value_counts(normalize=True).sort_index()

        return {
            "Average Monthly Posting Frequency": avg_monthly_posts,
            "Average Post Length": avg_post_length,
            "Average Likes on Media Posts": avg_likes_media,
            "Average Comments on Media Posts": avg_comments_media,
            "Likes Distribution": likes_dist,
            "Comments Distribution": comments_dist,
            "Shares Distribution": shares_dist,
        }

    def visualize_metrics(self, metrics: Dict):
        if not metrics:
            print("No metrics available to visualize.")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        ax1.bar(["Likes", "Comments"], [metrics["Average Likes on Media Posts"], metrics["Average Comments on Media Posts"]])
        ax1.set_title("Average Engagement on Media Posts")
        ax1.set_ylabel("Average Engagement")

        ax2.plot(metrics["Likes Distribution"].index, metrics["Likes Distribution"], label="Likes")
        ax2.plot(metrics["Comments Distribution"].index, metrics["Comments Distribution"], label="Comments")
        ax2.plot(metrics["Shares Distribution"].index, metrics["Shares Distribution"], label="Shares")
        ax2.set_title("Engagement Distribution")
        ax2.set_xlabel("Engagement Count")
        ax2.set_ylabel("Percentage")
        ax2.legend()

        plt.savefig("linkedin_post_analytics.png")
        print("Metrics visualization saved as 'linkedin_post_analytics.png'.")

    def run(self):
        self.login()
        self.process_post_data()
        metrics = self.calculate_metrics()
        self.visualize_metrics(metrics)

        print("LinkedIn Post Analysis Complete.")
        self.driver.quit()

urls_to_add = [
    "https://www.linkedin.com/in/psmahesh/",
    "https://www.linkedin.com/in/saheli-chatterjee-organic-marketing/",
    "https://www.linkedin.com/in/gunjan-kanodia/" ,
    "https://www.linkedin.com/in/bhavya-goel-b927a71a4/"
]

def add_urls_to_redis(urls):
    try:
        # Connect to Redis
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        
        # Add each URL to the Redis list
        for url in urls:
            redis_client.rpush("linkedin_urls", url)
            print(f"Added URL to Redis: {url}")
    except Exception as e:
        print(f"Error adding URLs to Redis: {e}")
if __name__ == "__main__":
    add_urls_to_redis(urls_to_add)
    analyzer = LinkedInPostAnalyzer()
    analyzer.run() 