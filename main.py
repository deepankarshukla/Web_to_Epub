import os
import time
import json
import random
import logging
from ebooklib import epub
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# ================= CONFIG =================
MAX_THREADS = min(6, os.cpu_count() * 2)
PROGRESS_FILE = "progress.json"
SAVE_HTML = False   # set True if you want raw chapter backup
HEADERS_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
]

# ================= LOGGING =================
logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ================= SESSION =================
def create_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# ================= PROGRESS =================
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return set(json.load(f))
    return set()

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(list(progress), f)

# ================= CLEAN HTML =================
def clean_html(content):
    for tag in content(["script", "style", "ins", "ads"]):
        tag.decompose()

    for img in content.find_all("img"):
        img['style'] = "max-width:100%; height:auto;"

    return str(content)

# ================= FETCH =================
def fetch_chapter(i, base_url, session, completed):
    if i in completed:
        return None

    try:
        url = f"{base_url}{i}"

        headers = {
            "User-Agent": random.choice(HEADERS_LIST)
        }

        response = session.get(url, headers=headers, timeout=20)

        # Smart delay
        time.sleep(random.uniform(1, 3))

        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        title_tag = soup.find('span', class_='chapter')
        title = title_tag.get_text().strip() if title_tag else f"Chapter {i}"

        content = soup.find('div', {'id': 'article'})
        if not content:
            logging.warning(f"No content for Chapter {i}")
            return None

        # Validate content
        if len(content.get_text(strip=True)) < 100:
            logging.warning(f"Empty content Chapter {i}")
            return None

        content = clean_html(content)

        # Optional backup
        if SAVE_HTML:
            os.makedirs("chapters", exist_ok=True)
            with open(f"chapters/chap_{i}.html", "w", encoding="utf-8") as f:
                f.write(content)

        logging.info(f"Fetched Chapter {i}")
        return (i, title, content)

    except requests.exceptions.Timeout:
        logging.error(f"Timeout Chapter {i}")
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection Error Chapter {i}")
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error Chapter {i}: {e}")
    except Exception as e:
        logging.error(f"Unknown Error Chapter {i}: {e}")

    return None

# ================= EPUB BUILDER =================
def create_epub(chapters_data, output_file, book_title):
    book = epub.EpubBook()
    book.set_identifier('id123456')
    book.set_title(book_title)
    book.set_language('en')
    book.add_author("Auto Scraper")

    # CSS
    style = """
    body { font-family: Arial; line-height: 1.6; padding:10px; }
    h1 { text-align:center; }
    p { margin:10px 0; }
    """
    css = epub.EpubItem(uid="style", file_name="style.css",
                        media_type="text/css", content=style)
    book.add_item(css)

    chapters = []
    spine = ['nav']

    for i, title, content in chapters_data:
        chapter = epub.EpubHtml(
            title=title,
            file_name=f'chap_{i}.xhtml',
            lang='en'
        )

        chapter.content = f"<h1>{title}</h1>{content}"
        chapter.add_item(css)

        book.add_item(chapter)
        chapters.append(chapter)
        spine.append(chapter)

    book.toc = chapters
    book.spine = spine

    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())

    epub.write_epub(output_file, book)

# ================= MAIN =================
def create_epub_from_url(base_url, chapter_count, output_file, book_title):
    completed = load_progress()
    chapters_data = []

    with create_session() as session:
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {
                executor.submit(fetch_chapter, i, base_url, session, completed): i
                for i in range(1, chapter_count + 1)
            }

            for future in tqdm(as_completed(futures), total=len(futures)):
                result = future.result()
                if result:
                    chapters_data.append(result)
                    completed.add(result[0])

                    # Save progress continuously
                    save_progress(completed)

    # Sort chapters
    chapters_data.sort(key=lambda x: x[0])

    create_epub(chapters_data, output_file, book_title)

    print(f"\n🎉 EPUB created: {output_file}")

# ================= ENTRY =================
def main():
    base_url = "https://freewebnovel.com/novel/reverand-insanity/chapter-"
    chapter_count = 2334
    output_file = "reverand-insanity.epub"
    book_title = "reverand-insanity"

    create_epub_from_url(base_url, chapter_count, output_file, book_title)

if __name__ == "__main__":
    main()