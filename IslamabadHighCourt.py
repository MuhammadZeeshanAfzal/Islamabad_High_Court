import os
import time
import json
import requests
from selenium.webdriver.support.select import Select
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, StaleElementReferenceException


def check_internet(url="http://www.google.com", timeout=5, interval=10):
    """Check if the internet is connected."""
    while True:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                print("Internet is connected.")
                return True
        except requests.ConnectionError:
            print(f"Connection failed. Retrying in {interval} seconds...")
        time.sleep(interval)


def initialize_driver(download_directory):
    """Initialize the Chrome WebDriver with specified download directory."""
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(download_directory),
        "download.prompt_for_download": False,
        "directory_upgrade": True,
    })
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("Driver initialized successfully.")
        return driver
    except WebDriverException as e:
        print(f"Error initializing WebDriver: {e}")
        return None


def navigate_to_page(driver):
    """Navigate to the desired page and handle iframe switching."""
    try:
        driver.maximize_window()
        print("Navigating to the page...")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))

        iframe = driver.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)

        # Click the required options
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "liMdtn"))).click()
        time.sleep(2)
        options = driver.find_elements(By.XPATH, '//*[@id="liMdtn"]/ul/li[5]')
        if options:
            options[0].click()
        else:
            print("No matching element found for the XPath")

        # Final steps to reach the page with the data
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="page-top"]/div[2]/div[3]/div[1]/div/strong[3]/a'))).click()
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="rdt6"]/b'))).click()
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSearch"]'))).click()

        print("Successfully navigated to the desired page.")
        time.sleep(5)
    except TimeoutException as e:
        print(f"Navigation timeout: {e}")
    except Exception as e:
        print(f"Error while navigating: {e}")


def download_pdf(url, folder_path, file_name):
    try:
        # Create folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)

        # Define the file path where the PDF will be saved
        file_path = os.path.join(folder_path, file_name)

        # Send a GET request to the URL to download the PDF
        response = requests.get(url, stream=True)

        # Check if the request was successful
        if response.status_code == 200:
            # Write the content of the response (PDF) to the file
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            print(f"PDF downloaded successfully: {file_path}")
        else:
            print(f"Failed to download PDF. Status code: {response.status_code}")

    except requests.RequestException as e:
        print(f"Error downloading PDF: {e}")


def save_to_json_incremental(data, json_filename):
    """Save data to the specified JSON file, appending it to the existing content."""
    try:
        # Ensure data is in the correct format before saving
        if not data or not isinstance(data, dict):
            print(f"Invalid data: {data}")
            return

        existing_data = []
        if os.path.exists(json_filename):
            with open(json_filename, "r", encoding="utf-8") as f:
                existing_data = json.load(f)

        existing_data.append(data)

        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        print(f"Data saved to {json_filename}")
    except Exception as e:
        print(f"Error saving data: {e}")


def print_html_with_selenium(url):
    """Fetch HTML content of a page using Selenium."""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode (optional)
        driver = webdriver.Chrome(options=chrome_options)

        driver.get(url)
        html_content = driver.page_source
        return html_content

    except Exception as e:
        print(f"Error fetching HTML with Selenium: {e}")
    finally:
        driver.quit()
def scrape_visible_page_data(driver, json_filename, folder_path):
    """Scrape data from visible rows on the page."""
    try:
        i = 1
        while True:
            row_xpath = f'//*[@id="dvMain"]/div[{i}]'
            try:
                # Use explicit wait for row to be visible
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, row_xpath))
                )

                row = driver.find_element(By.XPATH, row_xpath)
                pdf_href = ""
                case_no = row.find_element(By.XPATH, './/*[@id="cseNo"]').text
                description = row.find_element(By.XPATH, './/*[@id="cseDsc"]').text
                discussed_laws = row.find_element(By.XPATH, './/*[@id="cseDscLws"]').text
                case_title = row.find_element(By.XPATH, './/*[@id="cseTle"]').text
                author_judge = row.find_element(By.XPATH, './/*[@id="cseAthr"]').text
                judgment_date = row.find_element(By.CSS_SELECTOR, "cite.text-danger.pull-left").text
                case_citation = row.find_element(By.XPATH, './/*[@id="cseCit"]').text

                # Try to fetch the download link
                try:
                    download_button = row.find_element(By.XPATH, './/*[@id="dwnld"]/a')
                    new = download_button.get_attribute('href')
                    html_content = print_html_with_selenium(new)
                    soup = BeautifulSoup(html_content, 'html.parser')

                    pdf_link = soup.find('a', href=True)
                    if pdf_link:
                        pdf_href = pdf_link['href']
                        print("PDF URL........................................................:", pdf_href)
                    else:
                        print("PDF URL not found")

                except NoSuchElementException as e:
                    print(f"Error fetching download link: {e}")
                except Exception as e:
                    print(f"Unexpected error during download process: {e}")

                # Store the case details
                case_details = {
                    "caseNo": case_no,
                    "description": description,
                    "discussedLaws": discussed_laws,
                    "caseTitle": case_title,
                    "authorJudge": author_judge,
                    "judgmentDate": judgment_date,
                    "caseCitation": case_citation,
                    "URL": pdf_href
                }

                save_to_json_incremental(case_details, json_filename)
                print(f"Scraped case: {case_no}")
                # download_pdf(pdf_href, folder_path, case_no)

                # Scroll the page if needed
                driver.execute_script("window.scrollBy(0, 580);")  # Adjust the scroll value as necessary
                time.sleep(2)
                i += 1

            except StaleElementReferenceException:
                print(f"Stale element reference. Retrying for row {i}...")
                continue  # Skip and retry

            except NoSuchElementException:
                print(f"No more rows found. Scraping completed.")
                break
            except WebDriverException as e:
                print(f"WebDriverException caught: {e}")
                if "no such window" in str(e):
                    print("Attempting to recover by reinitializing the driver.")
                    driver.quit()
                    driver = initialize_driver(folder_path)  # Reinitialize driver
                    driver.get("https://www.ihc.gov.pk/")  # Retry loading the page
                    navigate_to_page(driver)  # Retry navigating
                    i = 1  # Restart from the first row
                    continue
            except Exception as e:
                print(f"Error processing row {i}: {e}")
                i += 1
    except Exception as e:
        print(f"Unexpected error while scraping: {e}")

def main(json_filename, folder_path):
    """Main function to execute the scraping process."""
    check_internet()
    os.makedirs(folder_path, exist_ok=True)

    driver = initialize_driver(folder_path)
    if driver:
        try:
            driver.get("https://www.ihc.gov.pk/")
            time.sleep(10)
            navigate_to_page(driver)
            scrape_visible_page_data(driver, json_filename, folder_path)
        finally:
            driver.quit()


if __name__ == "__main__":
    json_filename = "IslamabadHighCourt.json"
    folder_path = "IslamabadHighCourtJudgements"
    main(json_filename, folder_path)
