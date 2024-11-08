import os
import time
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse
import random
import pandas as pd
from matplotlib import pyplot as plt
import mysql.connector

class connect:
    def __init__(self):
        try:
            self.db_connection = self.create_db_connection()
            self.create_table_if_not_exists()
        except Exception as e:
            print(f"Error connecting to database: {e}")
        self.post_data = []

    def create_db_connection(self):
        try:
            connection = mysql.connector.connect(
                host= "localhost",    
                user= "user",
                password= "forgot",
                database= "Linkedindata"
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

    def run(self):
        try:
            if True:
                for post in "hi":
                    self.insert_post_data_to_db(post)
                print("Data saved to MySQL database successfully.")
        except Exception as e:
            print(f"Error during analysis: {e}")
        finally:
            self.driver.quit()
            if self.db_connection.is_connected():
                self.db_connection.close()
                print("MySQL connection is closed")

if __name__ == "__main__":
    analyzer = connect()
    analyzer.run() 