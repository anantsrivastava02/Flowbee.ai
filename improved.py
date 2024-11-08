import os
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse
import random
import pandas as pd
import redis
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from matplotlib import pyplot as plt
import mysql.connector

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
USER = os.getenv("USER")
PASSWORDD = os.getenv("PASSWORDD")
DATABASE = os.getenv("DATABASE")
URL = os.getenv("URL")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))  # Default to 6379 if not set
REDIS_DB = int(os.getenv("REDIS_DB", 0)) 

CHROME_OPTIONS = Options()
CHROME_OPTIONS.add_argument("--no-sandbox")
CHROME_OPTIONS.add_argument("--disable-dev-shm-usage")
CHROME_OPTIONS.add_argument("--disable-gpu")
CHROME_OPTIONS.add_argument("--window-size=1920,1080")
CHROME_OPTIONS.add_argument("--disable-notifications")
CHROME_OPTIONS.add_argument("--disable-popup-blocking")
CHROME_OPTIONS.add_argument("--start-maximized")
CHROME_OPTIONS.add_argument("--disable-blink-features=AutomationControlled")
CHROME_OPTIONS.add_argument("--disable-webgl")
CHROME_OPTIONS.add_argument("--disable-3d-apis")
CHROME_OPTIONS.add_argument("--disable-gpu-sandbox")
CHROME_OPTIONS.add_argument("--disable-accelerated-2d-canvas")
CHROME_OPTIONS.add_argument("--disable-accelerated-video-decode")
CHROME_OPTIONS.add_argument("--disable-webrtc")
CHROME_OPTIONS.add_experimental_option("excludeSwitches", ["enable-automation"])
CHROME_OPTIONS.add_experimental_option("useAutomationExtension", False)
CHROME_OPTIONS.add_argument("--disable-blink-features=WebRTC")
class LinkedInPostAnalyzer:
    def __init__(self):
        try:
            self.driver = webdriver.Chrome(options=CHROME_OPTIONS)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            raise
        try:
            self.db_connection = self.create_db_connection()
            self.create_table_if_not_exists()
        except Exception as e:
            print(f"Error connecting to database: {e}")
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

    def create_db_connection(self):
        try:
            connection = mysql.connector.connect(
                host= HOST,    
                user= USER,
                password=PASSWORDD,
                database= DATABASE
            )
            return connection
        except Exception as e:
            print(f"Error connecting to MySQL Database: {e}")
            raise

    def create_table_if_not_exists(self):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS posts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            post_text TEXT,
            media_link TEXT,
            media_type VARCHAR(255),
            post_date DATE,
            likes INT,
            comments INT,
            shares INT
        );
        """
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(create_table_query)
            self.db_connection.commit()
        except Exception as e:
            print(f"Failed to create table: {e}")
        finally:
            cursor.close()

    def insert_post_data_to_db(self, post_data):
        insert_query = """
        INSERT INTO posts (post_text, media_link, media_type, post_date, likes, comments, shares)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(insert_query, (
                post_data['Post Text'],
                post_data['Media Link'],
                post_data['Media Type'],
                post_data['Post Date'],
                post_data['Likes'],
                post_data['Comments'],
                post_data['Shares']
            ))
            self.db_connection.commit()
            print("Post data inserted successfully")
        except Exception as e:
            print(f"Failed to insert post data: {e}")
        finally:
            cursor.close()

    def scrape_post_data(self, url: str) -> Dict:
        
        base_url = url.split('?')[0].split('/overlay/')[0]
        if not base_url.endswith('/'):
            base_url += '/'
            
        print(f"Accessing URL: {base_url}")
        self.driver.get(base_url)
        time.sleep(10)
        self.scroll_page()
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feed-shared-update-v2"))
            )
        except TimeoutException:
            print(f"No posts found on page: {base_url}")
            return {}      
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        post_text = self.get_post_text(soup)
        media_link, media_type = self.get_media_info(soup)
        post_date = self.get_post_date(soup)
        post_reactions = self.get_post_reactions(soup)
        post_comments = self.get_post_comments(soup)
        post_shares = self.get_post_shares(soup)
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
        
    def extract_new_urls(self, soup: BeautifulSoup) -> List[str]:
        new_urls = []
        for link in soup.find_all("a", href=True):
            url = link["href"]
            if "linkedin.com/in/" in url or "linkedin.com/company/" in url:
                new_urls.append(url)
        return [] #list(set(new_urls))
    
    def scroll_page(self):
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(100):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(10)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
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
        time_element = soup.find("a", class_="app-aware-link update-components-actor__sub-description-link")
        
        if time_element:
            span_element = time_element.find("span", class_="update-components-actor__sub-description")
            if span_element and span_element.text.strip():
                time_text = span_element.text.strip().split("•")[0].strip()  
                print(time_text)
                return self.get_actual_date(time_text)
        
        return ""

    def get_actual_date(self, date_str: str) -> str:
        today = datetime.today()
        current_year = today.year
        match = re.match(r"(\d+)([hdwmy])", date_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            if unit == "h": 
                return today.strftime("%Y-%m-%d")
            elif unit == "d": 
                return (today - timedelta(days=value)).strftime("%Y-%m-%d")
            elif unit == "w": 
                return (today - timedelta(weeks=value)).strftime("%Y-%m-%d")
            elif unit == "m": 
                return (today - timedelta(days=30 * value)).strftime("%Y-%m-%d")
            elif unit == "y":
                return (today - timedelta(days=365 * value)).strftime("%Y-%m-%d")
        
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
        
        return ""

    def get_post_reactions(self, soup: BeautifulSoup) -> int:
        reactions_element = soup.find("span", class_="social-details-social-counts__reactions-count")
        
        if reactions_element and reactions_element.text.strip() != "":
            reactions_text = reactions_element.text.strip().replace(',', '')
            return int(reactions_text)
        
        return 0

    def get_post_comments(self, soup: BeautifulSoup) -> int:
        repost_elements = soup.find_all(
            lambda tag: tag.name == "button" and "aria-label" in tag.attrs and "comment" in tag["aria-label"].lower()
        )
        if not repost_elements:
            return 0
        repost_element = repost_elements[0]
        text = repost_element.get("aria-label", "").strip()
        import re
        numbers = re.findall(r'\d+', text.replace(',', ''))
        if numbers:
            number_str = ''.join(numbers)
            return int(number_str)
        else:
            return 0

    def get_post_shares(self, soup: BeautifulSoup) -> int:
        repost_elements = soup.find_all(
            lambda tag: tag.name == "button" and "aria-label" in tag.attrs and "reposts" in tag["aria-label"].lower()
        )
        if not repost_elements:
            return 0
        repost_element = repost_elements[0]
        text = repost_element.get("aria-label", "").strip()
        import re
        numbers = re.findall(r'\d+', text.replace(',', ''))
        if numbers:
            number_str = ''.join(numbers)
            return int(number_str)
        else:
            return 0

    def process_post_data(self):
        count = 0
        while count < 10:
            url = self.redis_client.lpop("linkedin_urls")
            if not url:
                break
            url = url.decode("utf-8")
            post_data = self.scrape_post_data(url)
            if post_data:
                self.post_data.append(post_data)
                count += 1
                print(f"Successfully processed post from URL: {url}")
            else:
                print(f"Failed to process post from URL: {url}")
            time.sleep(random.uniform(3, 7))
            
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
        try:
            self.login()
            self.process_post_data()
            if self.post_data:
                for post in self.post_data:
                    self.insert_post_data_to_db(post)
                print("Data saved to MySQL database successfully.")
            metrics = self.calculate_metrics()

            self.visualize_metrics(metrics)
            print("LinkedIn Post Analysis Complete.")
        except Exception as e:
            print(f"Error during analysis: {e}")
        finally:
            self.driver.quit()
            if self.db_connection.is_connected():
                self.db_connection.close()
                print("MySQL connection is closed")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
redis_client.delete("linkedin_urls")

urls_to_add = [
    "https://www.linkedin.com/in/bhavya-goel-b927a71a4/",
]
urls_to_add.append(URL)
def add_urls_to_redis(urls):
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    for base_url in urls:
        url_recent_activity = f"{base_url}recent-activity/all/"
        url_posts = f"{base_url}posts/?feedView=all"
        redis_client.rpush("linkedin_urls", base_url)
        redis_client.rpush("linkedin_urls", url_recent_activity)
        redis_client.rpush("linkedin_urls", url_posts)
    
if __name__ == "__main__":
    
    add_urls_to_redis(urls_to_add)
    analyzer = LinkedInPostAnalyzer()
    analyzer.run() 