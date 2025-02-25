from selenium import webdriver
from selenium.webdriver.common.by import By

# Set up the webdriver (e.g., ChromeDriver)
driver = webdriver.Chrome()

# Open the website
driver.get("https://ftnfantasy.com/dfs/nfl/ownership-projections")

# Find and click the "CSV" button
csv_button = driver.find_element(By.XPATH, "/html/body/div[1]/main/section[2]/div/div[2]/div[2]/div[1]/button[3]/span]")
csv_button.click()

# Wait for the download to complete, if necessary
import time
time.sleep(5)

driver.quit()

