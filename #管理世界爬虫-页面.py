from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# Parameters
papers_need = None
start_date_str = "2019-01-01"
end_date_str = "2024-08-05"
search_type = "文献来源"  # "文献来源" or "关键词"等
search_text = "管理世界"
output_file = f'CNKI_{search_text}.csv'

# Convert date strings to datetime objects
start_date_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

def open_page(driver, theme, search_type):
    driver.get("https://www.cnki.net")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'DBFieldBox'))).click()
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, f"//div[@id='DBFieldList']//a[text()='{search_type}']"))
    ).click()
    search_box = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'txt_SearchText')))
    search_box.clear()
    search_box.send_keys(theme)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'search-btn'))).click()
    time.sleep(5)

def crawl(driver, papers_need, theme, start_date=None, end_date=None, output_file="output.csv"):
    count = 1

    try:
        while (not papers_need) or (count <= papers_need):
            titles = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "fz14"))
            )
            publish_dates = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//*[@id='gridTable']/div/div/div/table/tbody/tr/td[5]"))
            )
            sources = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[@target='_blank']/font"))
            )

            for title, publish_date, source in zip(titles, publish_dates, sources):
                publish_date_text = publish_date.text
                source_text = source.text
                
                if search_text not in source_text:
                    continue

                try:
                    publish_date_dt = datetime.strptime(publish_date_text.split()[0], "%Y-%m-%d")
                except ValueError:
                    print(f"Error in date format: {publish_date_text}")
                    publish_date_dt = None

                if publish_date_dt is not None:
                    if publish_date_dt < start_date_dt:
                        print(f"Stopping crawl as publish date {publish_date_text} < start date {start_date_str}.")
                        return
                    if end_date and publish_date_dt > end_date_dt:
                        print(f"Skipping publication date {publish_date_text} as it is beyond end date {end_date_str}.")
                        continue

                driver.execute_script("arguments[0].click();", title)
                driver.switch_to.window(driver.window_handles[1])
                data = extract_data(driver)
                data['publish_date'] = publish_date_text
                save_data(data, output_file)
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                count += 1
                if papers_need and count > papers_need:
                    return

            if not navigate_next_page(driver):
                break
    except Exception as e:
        print(f"Error during data crawling: {e}")

def extract_data(driver):
    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".wx-tit h1")))
        title = driver.find_element(By.CSS_SELECTOR, ".wx-tit h1").text.strip()
    except Exception as e:
        title = "Title not found"
        print(f"Failed to get the title: {e}")
        
    try:
        authors = driver.find_element(By.CSS_SELECTOR, ".author").text.strip()
    except Exception as e:
        authors = "Authors not found"
        print(f"Failed to get the authors: {e}")

    try:
        abstract = driver.find_element(By.ID, "ChDivSummary").text.strip()
    except Exception as e:
        abstract = "Abstract not found"
        print(f"Failed to get the abstract: {e}")
    
    try:
        keywords = ', '.join([elem.text for elem in driver.find_elements(By.CSS_SELECTOR, ".keywords a")])
    except Exception as e:
        keywords = "Keywords not found"
        print(f"Failed to get the keywords: {e}")

    return {'title': title, 'authors': authors, 'abstract': abstract, 'keywords': keywords}

def save_data(data, filename):
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', encoding='utf-8') as file:
        if not file_exists:
            file.write("Title,Authors,Publish Date,Keywords,Abstract\n")
        
        file.write(f'"{data["title"]}","{data["authors"]}","{data["publish_date"]}","{data["keywords"]}","{data["abstract"]}"\n')

def navigate_next_page(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "PageNext"))
        )
        next_page = driver.find_element(By.ID, "PageNext")
        next_page.click()
        time.sleep(3)
        return True
    except Exception as e:
        print(f"No more pages or failed to click on next page: {e}")
        return False

if __name__ == "__main__":
    driver = webdriver.Chrome()
    open_page(driver, search_text, search_type)
    crawl(driver, papers_need, search_text, start_date_str, end_date_str, output_file)
    driver.quit()
