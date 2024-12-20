from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
import time
import base64
import pandas as pd
import os
import webbrowser
import sqlite3
from PIL import Image
import pytesseract
import openai
import requests
from selenium.webdriver.chrome.options import Options


# Configuration
CHROMEDRIVER_PATH = "chromedriver.exe"
OUTPUT_FOLDER = "output"
DB_NAME = "linkedin_profiles.db"
OPENAI_API_KEY = "Enter an OpenAPI key"
pytesseract.pytesseract.tesseract_cmd = r"mention the teseract location"

# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# Selenium Setup
def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--disable-webrtc")  # Disable WebRTC
    chrome_options.add_argument("--disable-gpu")  # Disable GPU rendering
    chrome_options.add_argument("--log-level=3")  # Suppress logs
    chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
)

    cService = ChromeService(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=cService, options=chrome_options)
    driver.set_window_size(1920, 1080)
    
    return driver

# Login to LinkedIn
def linkedin_login(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)
    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(5)  # Wait for login

# Take screenshot of LinkedIn profile
def save_full_page_as_image(driver, profile_url, name):
    try:
        print(f"Opening profile for {name}...")
        driver.get(profile_url)

        print(f"Page loaded for {name}. Capturing full-page screenshot...")
        time.sleep(5)
        # Use Chrome DevTools Protocol to capture a full-page screenshot
        screenshot_data = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})

        # Decode the Base64 data
        screenshot_path = os.path.join(OUTPUT_FOLDER, f"{name}_fullpage.png")
        with open(screenshot_path, "wb") as f:
            f.write(base64.b64decode(screenshot_data["data"]))

        print(f"Full-page screenshot saved successfully for {name} at {screenshot_path}")
        return screenshot_path

    except Exception as e:
        print(f"Error capturing full-page screenshot for {name}: {e}")
        return None


# Extract text using Tesseract (as a backup for OpenAI OCR)

def extract_text_from_image(image_path):
    """
    Extract text from an image using Tesseract OCR.
    """
    try:
        print(f"Extracting text from image at {image_path}...")
        text = pytesseract.image_to_string(Image.open(image_path))
        print(f"Extracted Text: {text[:100]}...")  # Preview extracted text
        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""

def send_text_to_openai(extracted_text):
    """
    Send the extracted text to OpenAI for further processing.
    """
    try:
        # OpenAI API endpoint for GPT models
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4",  # Use the model of your choice
            "messages": [
                {"role": "system", "content": "You are an AI that processes and improves extracted text."},
                {"role": "user", "content": extracted_text}
            ]
        }
        
        # Make the request
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        
        if response.status_code == 200:
            processed_text = response_data['choices'][0]['message']['content']
            print(f"Processed Text: {processed_text}")
            return processed_text
        else:
            print(f"Error: {response_data}")
            return ""
    except Exception as e:
        print(f"Error sending text to OpenAI: {e}")
        return ""


# Save extracted text to database
def save_to_database(name, mobile, linkedin_url, extracted_text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT,
            MobileNumber TEXT,
            LinkedInURL TEXT,
            ExtractedText TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO Profiles (Name, MobileNumber, LinkedInURL, ExtractedText)
        VALUES (?, ?, ?, ?)
    """, (name, mobile, linkedin_url, extracted_text))
    conn.commit()
    conn.close()
    print(f"Saved {name} to database.")

# Generate personalized cold email
def craft_email(name, extracted_text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role": "system", "content": "You are an AI assistant that crafts personalized emails."},
        {"role": "user", "content": f"Enter the type of mail needed to be drafted"}
    ]
    
    # Prepare the data payload
    data = {
        "model": "gpt-4",  # Specify the model you wish to use
        "messages": messages,
        "max_tokens": 400,
        "temperature": 0.7
    }
    
    try:
        # Make the request to the OpenAI API
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an error for unsuccessful requests
        response_data = response.json()
        
        # Extract the generated email content
        email_content = response_data['choices'][0]['message']['content'].strip()
        return email_content
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return ""
    except KeyError:
        print("Unexpected response structure.")
        return ""
# Main function
def main():
    # Input file
    input_file = "Enter the Excel Sheet location"
    data = pd.read_excel(input_file)

    # Selenium browser setup
    driver = setup_browser()

    try:
        #Login credentials
        linkedin_email = "Enter a temperarory Email id"
        linkedin_password = "Enter password"

        # Log in to LinkedIn
        linkedin_login(driver, linkedin_email, linkedin_password)

        for index, row in data.iterrows():
            name = row["Name"]
            linkedin_url = row["LinkedInProfileURL"]
            mobile = row["Mobile Number"]

            try:
                # Step 1: Open LinkedIn profile and save as image
                image_path = save_full_page_as_image(driver, linkedin_url, name)

                # Step 2: Extract text from image
                # Step 1: Extract text from the image
                extracted_text = extract_text_from_image(image_path)

                # Step 2: Send the text to OpenAI for processing (optional)
                if extracted_text:
                    processed_text = send_text_to_openai(extracted_text)
                else:
                    print("No text extracted from the image.")

                # Step 3: Save to database
                save_to_database(name, mobile, linkedin_url, processed_text)
                openai.api_key = "Enter APi Key"
                
                # Step 4: Generate cold email
                email = craft_email(name, extracted_text)
                print(f"Generated email for {name}:\n{email}\n")

            except Exception as e:
                print(f"Error processing {name}: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
