import os
import re
import requests
import logging
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_BASE_URL = os.getenv("CLOUDFLARE_API_BASE_URL")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/convert_images.log")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "_posts")
ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", "drafts/archived")

# Configure logging
logging.basicConfig(level=logging.INFO, filename=LOG_FILE_PATH, filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")

def upload_image_to_cloudflare(image_path):
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"
    }
    files = {
        'file': open(image_path, 'rb')
    }
    try:
        response = requests.post(CLOUDFLARE_API_BASE_URL, headers=headers, files=files)
        if response.status_code == 200:
            logging.info(f"Successfully uploaded image: {image_path}")
            return response.json()["result"]["id"], response.json()["result"]["variants"][0]
        else:
            logging.error(f"Failed to upload image: {image_path}, Error: {response.text}")
            return None, None
    except Exception as e:
        logging.error(f"Exception occurred during image upload: {image_path}, Error: {str(e)}")
        return None, None

def git_commit_and_push(file_path, commit_message="Update blog post"):
    try:
        assets_dir = os.path.join(os.path.dirname(file_path), "../assets")
        subprocess.run(["git", "add", file_path, assets_dir], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push"], check=True)
        logging.info(f"Successfully committed and pushed {file_path} to Git.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Git operation failed: {e}")

def process_markdown_file(input_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()
    image_pattern = r'!\[.*?\]\((.*?)\)'
    matches = re.findall(image_pattern, content)
    updated_content = content

    for match in matches:
        local_image_path = os.path.join(os.path.dirname(input_file), match)
        if os.path.exists(local_image_path):
            logging.info(f"Found image for upload: {local_image_path}")
            image_id, image_url = upload_image_to_cloudflare(local_image_path)
            if image_url:
                updated_content = updated_content.replace(match, image_url)
                logging.info(f"Replaced {match} with {image_url}")
            else:
                logging.error(f"Failed to process image: {local_image_path}")
        else:
            logging.warning(f"Image not found: {local_image_path}")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    output_file = os.path.join(OUTPUT_DIR, os.path.basename(input_file))
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(updated_content)

    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
    archived_file = os.path.join(ARCHIVE_DIR, os.path.basename(input_file))
    os.rename(input_file, archived_file)

    logging.info(f"Processed {input_file} and saved to {output_file}")
    git_commit_and_push(output_file, commit_message=f"Publish post {os.path.basename(output_file)}")

def main():
    input_file = input("Enter the path to the Markdown file: ").strip()
    if not os.path.exists(input_file):
        logging.error(f"Input file does not exist: {input_file}")
        print(f"File {input_file} does not exist.")
        return
    process_markdown_file(input_file)
    logging.info(f"Completed processing for file: {input_file}")
    print(f"Processed {input_file}. Check logs for details.")

if __name__ == "__main__":
    main()
