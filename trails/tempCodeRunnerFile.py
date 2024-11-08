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
        