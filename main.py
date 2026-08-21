import time
from enum import verify

from ebooklib import epub
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


MAX_THREADS = 2


def fetch_chapter(i, base_url, session):
    try:
        chapter_url = f"{base_url}{i}"
        response = session.get(chapter_url, timeout=20, verify=False)
        time.sleep(5)  # ⏱️ KEEPING SLEEP AS REQUESTED
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        chapter_title_element = soup.find('span', class_='chapter')
        chapter_title = (
            chapter_title_element.get_text().strip()
            if chapter_title_element else f"Chapter {i}"
        )

        content = soup.find('div', {'id': 'article'})
        if content is None:
            print(f"⚠️ No content for Chapter {i}")
            return None

        back_to_toc_button = """
<hr>
<p style="text-align:center;">
  <a href="nav.xhtml" style="text-decoration:none;">
    <button style="padding:10px 20px; background-color:#28a745; color:white;
                   border:none; border-radius:5px; font-size:16px;">
      🔙 Back to Contents
    </button>
  </a>
</p>
"""

        full_content = f"<h1>{chapter_title}</h1>\n{str(content)}\n{back_to_toc_button}"

        print(f"✅ Fetched {chapter_title}")
        return (i, chapter_title, full_content)

    except Exception as e:
        print(f"❌ Error Chapter {i}: {e}")
        return None


def create_epub_from_url(base_url, chapter_count, output_file, book_title="E-Book"):
    book = epub.EpubBook()
    book.set_identifier('id23456')
    book.set_title(book_title)
    book.set_language('en')

    chapters_data = []

    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = [
                executor.submit(fetch_chapter, i, base_url, session)
                for i in range(2863, chapter_count + 1)
            ]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    chapters_data.append(result)

    # Preserve chapter order
    chapters_data.sort(key=lambda x: x[0])

    toc = []
    spine = ['nav']

    for i, title, content in chapters_data:
        chapter = epub.EpubHtml(
            title=title,
            file_name=f'chap_{i}.xhtml',
            lang='en'
        )
        chapter.content = content

        book.add_item(chapter)
        toc.append(chapter)
        spine.append(chapter)

    book.toc = toc
    book.spine = spine

    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())

    epub.write_epub(output_file, book, {})
    print(f"\n🎉 EPUB created successfully: {output_file}")


def main():
    base_url = "https://freewebnovel.com/novel/keyboard-immortal-novel/chapter-"
    chapter_count = 2993
    output_file = "keyboard-immortal-2815-2945.epub"
    book_title = "keyboard-immortal-2815-2945"

    create_epub_from_url(base_url, chapter_count, output_file, book_title)


if __name__ == "__main__":
    main()