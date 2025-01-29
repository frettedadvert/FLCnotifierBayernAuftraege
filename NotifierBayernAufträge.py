import requests
import yagmail
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logging

websites = [
    {"url": "https://www.auftraege.bayern.de/Dashboards/Dashboard_off?BL=09", "keywords": ["catering", "verpflegung", "lebensmittel", "kantin", "speise", "hotel", "essen"]},
]

# Email configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MATCHES_FILE = os.path.join(SCRIPT_DIR, "matches.json")
TEXT_PARTS_FILE = "extracted_text_parts.json"

def load_previous_matches():
    """Load previously found matches from a file."""
    if os.path.exists(MATCHES_FILE):
        with open(MATCHES_FILE, "r") as file:
            return json.load(file)
    return {}

def save_matches(matches):
    """Save matches to a file."""
    with open(MATCHES_FILE, "w") as file:
        json.dump(matches, file, indent=4)

def save_text_parts(text_parts):
    """Save extracted text parts to a file."""
    with open(TEXT_PARTS_FILE, "w") as file:
        json.dump(text_parts, file, indent=4)

def check_keywords_in_text(extracted_data, keywords):
    relevant_matches = []
    lower_keywords = [keyword.lower() for keyword in keywords]
    
    for data in extracted_data:
        text = data["title"].lower()
        if any(keyword in text for keyword in lower_keywords):
            print(f"Relevant Match Found: {data['title']}")
            relevant_matches.append({"part": data["title"], "link": data["link"]})
    
    return relevant_matches

def extract_titles_with_selenium(url):
    """
    Extract titles and links directly from a dynamically rendered webpage using Selenium.
    Returns an array of dictionaries containing the title and corresponding link.
    """
    extracted_data = []
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(url)
        
        try:
            WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'alle akzeptieren')]"))
            ).click()
            print("Cookies popup dismissed successfully.")
        except Exception:
            print("No cookies popup found.")
        
        wait = WebDriverWait(driver, 30)
        title_elements = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "BekSummary")))
        
        print(f"Found {len(title_elements)} elements with class 'BekSummary'.")
        
        for i, element in enumerate(title_elements, start=1):
            try:
                title = element.text.strip()
                link = element.get_attribute("href")
                
                if title:
                    extracted_data.append({"title": title, "link": link})
                    print(f"Extracted {i}: Title: {title}, Link: {link}")
                else:
                    print(f"Skipped element {i} due to empty title.")
            except Exception as e:
                print(f"Error extracting data from element {i}: {e}")
    
    except Exception as e:
        print(f"Error extracting titles with Selenium: {e}")
    
    finally:
        driver.quit()
    
    return extracted_data

def send_email(new_matches):
    """Send an email notification with titles and links."""
    subject = "Neue Ausschreibungen verfügbar!!"
    body = "Die folgenden neuen Übereinstimmungen wurden gefunden:\n\n"
    
    for match in new_matches:
        title = match.get("part", "No Title")
        link = match.get("link", "No Link")
        body += f"Title: {title}\nLink: {link}\n\n"
    
    try:
        yag = yagmail.SMTP(EMAIL_ADDRESS, EMAIL_PASSWORD)
        yag.send("Henrik.Hemmer@flc-group.de", subject, body)
        print("Email sent!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    """Main function to check websites and send emails."""
    previous_matches = load_previous_matches()
    print("Previous Matches:", previous_matches)
    new_matches = []
    
    for site in websites:
        url = site["url"]
        keywords = site["keywords"]
        
        extracted_data = extract_titles_with_selenium(url)
        save_text_parts(extracted_data)
        
        matches = check_keywords_in_text(extracted_data, keywords)
        
        if url not in previous_matches:
            previous_matches[url] = []
        
        for match in matches:
            if match not in previous_matches[url]:
                new_matches.append(match)
                previous_matches[url].append(match)
    
    if new_matches:
        send_email(new_matches)
    
    save_matches(previous_matches)

if __name__ == "__main__":
    main()
