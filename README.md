# Flowbee.ai

Flowbee.ai is a Python-based project for LinkedIn post analytics, leveraging MySQL for data storage and analysis. The project includes tools for scraping, analyzing, and visualizing LinkedIn post data, with support for Docker to streamline environment setup.

## Features

- **Data Collection**: Collects LinkedIn post data and stores it in a MySQL database.
- **Data Analysis**: Jupyter notebook (`analysis.ipynb`) for data insights.
- **Docker Support**: Simplifies setup with `Dockerfile` and `docker-compose.yml`.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/anantsrivastava02/Flowbee.ai.git
   ```

2. Configure environment variables in `.env` file.

3. Run with Docker:
   ```bash
   docker-compose up
   ```

## Requirements

- Python 3.11+
- MySQL
- Docker

## STEPS
   1- Run Redis Server on WSL using
   ```bash
   redis-server
   ```
     
  2- Create a Sql Database and config user, password, host, and database_name
  
  3- Setup .env file and add the required fields that include linkedin password and above config
  
  4- add url also
  
  5- Run poetry using
  ```bash
   poetry install
   ```
     
  6- Start the enviorment using
  ```bash
   poetry shell
   ```
     
  7- Run the improved.py
  

 ### OR 
 
  1- Run the docker image after setting up redis server 
  
## Design
### Given a Url Crawler goes to add three links to redis that are:

   #### given a profile link it add the recent-post as suffix to go to post page of person
   
   #### given a company link it add feed as suffix to go to post 
   
   #### and finally it adds the url also 

### Based on the page if it has nots then it will provide the following

   #### 1-reactions
   
   #### 2-date of post
   
   #### 3-comments
   
   #### 4-reposts
   
   #### 5-Media type

   #### 6-post
   
### and print succesfully data obtained else failed

### after that i defined two function that calulates frequency and every other related field given in ps and store the data in metrics and visualization image 

### dataframe gets returned in form of csv file 


### apart from that it adds the data to Mysql database 


## License

This project is licensed under the MIT License.
