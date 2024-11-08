if __name__ == "__main__":
    
    add_urls_to_redis(urls_to_add)
    analyzer = LinkedInPostAnalyzer()
    analyzer.run() 