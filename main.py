import time
from ebooklib import epub
from bs4 import BeautifulSoup
import requests


def create_epub_from_url(base_url, chapter_count, output_file, book_title="E-Book"):
    book = epub.EpubBook()
    book.set_identifier('id23456')
    book.set_title(book_title)
    book.set_language('en')

    chapter_links = []
    chapters = []
    toc = []

    for i in range(1, chapter_count + 1):
        try:
            chapter_url = f"{base_url}{i}"
            response = requests.get(chapter_url)
            time.sleep(2)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Get chapter title from span.chapter
            chapter_title_element = soup.find('span', class_='chapter')
            if chapter_title_element:
                chapter_title = chapter_title_element.get_text().strip()
            else:
                chapter_title = f"Chapter {i}"

            content = soup.find('div', {'id': 'article'})
            if content is None:
                print(f"Warning: No content found for Chapter {i}")
                continue

            chapter_text = str(content)
            chapter_file_name = f'chap_{i}.xhtml'
            chapter = epub.EpubHtml(title=chapter_title, file_name=chapter_file_name, lang='en')

            back_to_toc_button = """
<hr>
<p style="text-align:center;">
  <a href="nav.xhtml" style="text-decoration:none;">
    <button style="padding:10px 20px; background-color:#28a745; color:white; border:none; border-radius:5px; font-size:16px;">
      🔙 Back to Contents
    </button>
  </a>
</p>
"""
            full_content = f"<h1>{chapter_title}</h1>\n{chapter_text}\n{back_to_toc_button}"
            chapter.content = full_content

            chapters.append(chapter)
            chapter_links.append((chapter_title, chapter_file_name))
            print(f"{chapter_title} added successfully.")

        except Exception as e:
            print(f"Error processing Chapter {i}: {e}")

    # Add chapters to book and TOC
    for chapter in chapters:
        book.add_item(chapter)
        book.spine.append(chapter)
        toc.append(chapter)

    book.toc = toc  # Native EPUB Table of Contents

    # Required navigation files for EPUB
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())

    # Write EPUB file
    epub.write_epub(output_file, book, {})
    print(f"\n✅ ePub created successfully: {output_file}")


def main():
    base_url = "https://freewebnovel.com/novel/heavens-devourer-novel/chapter-"
    chapter_count = 1680
    output_file = "heavens-devourer.epub"
    book_title = "Heavens Devourer"

    create_epub_from_url(base_url, chapter_count, output_file, book_title)


if __name__ == "__main__":
    main()
