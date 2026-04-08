import time
import os
import requests
from ebooklib import epub
from bs4 import BeautifulSoup
import google.generativeai as genai


# --------------------------------------------
# Gemini Image Generator
# --------------------------------------------
genai.configure(api_key="AIzaSyA7_qMiXC8MdlH3SSJNbnqegOwEz-7eX7A")

def generate_chapter_image(chapter_title, chapter_number):
    """
    Generates comic-style illustration for the chapter using Gemini API.
    """
    prompt = (
        f"Create a dramatic, high-quality, comic-style illustration representing "
        f"'{chapter_title}'. It should look like a scene from a dark fantasy graphic novel, "
        f"with strong lighting, detailed characters, and atmospheric background."
    )

    model = genai.GenerativeModel("gemini-2.0-flash-lite")

    try:
        response = model.generate_images(
            prompt=prompt,
            size="1024x1024"
        )
        image_bytes = response.generated_images[0]

        filename = f"chapter_{chapter_number}.png"
        with open(filename, "wb") as f:
            f.write(image_bytes)

        print(f"   🎨 Image generated for: {chapter_title}")
        return filename

    except Exception as e:
        print(f"   ⚠️ Failed to generate image for {chapter_title}: {e}")
        return None


# --------------------------------------------
# EPUB Generator
# --------------------------------------------
def create_epub_from_url(base_url, chapter_count, output_file, book_title="E-Book"):
    book = epub.EpubBook()
    book.set_identifier('id23456')
    book.set_title(book_title)
    book.set_language('en')

    chapters = []
    toc = []

    for i in range(1, chapter_count + 1):
        try:
            chapter_url = f"{base_url}{i}"
            response = requests.get(chapter_url)
            time.sleep(1)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            title_element = soup.find('span', class_='chapter')
            chapter_title = title_element.get_text().strip() if title_element else f"Chapter {i}"

            content = soup.find('div', {'id': 'article'})
            if content is None:
                print(f"Warning: No content found for Chapter {i}")
                continue

            chapter_text = str(content)

            # -----------------------------
            # Generate image for chapter
            # -----------------------------
            image_file = generate_chapter_image(chapter_title, i)

            image_html = ""
            if image_file:
                # Add image as EPUB asset
                with open(image_file, "rb") as f:
                    img_item = epub.EpubItem(
                        uid=f"img_{i}",
                        file_name=f"images/{image_file}",
                        media_type="image/png",
                        content=f.read()
                    )
                book.add_item(img_item)

                # Embed image in chapter HTML
                image_html = (
                    f"<div style='text-align:center;'>"
                    f"<img src='images/{image_file}' style='width:100%; max-width:900px; border-radius:8px;'/>"
                    f"</div><br>"
                )

            # -----------------------------
            # Build chapter HTML
            # -----------------------------
            chapter_html = f"""
            <h1>{chapter_title}</h1>
            {image_html}
            {chapter_text}
            <hr>
            <p style="text-align:center;">
              <a href="nav.xhtml">
                <button style="padding:10px 20px; background-color:#28a745; color:white; border:none; border-radius:5px;">
                  🔙 Back to Contents
                </button>
              </a>
            </p>
            """

            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f'chap_{i}.xhtml',
                lang='en'
            )
            chapter.content = chapter_html

            chapters.append(chapter)
            print(f"✔️ {chapter_title} added.")

        except Exception as e:
            print(f"❌ Error processing Chapter {i}: {e}")

    # --------------------------------------------
    # Add chapters + TOC + spine
    # --------------------------------------------
    for chapter in chapters:
        book.add_item(chapter)
        book.spine.append(chapter)
        toc.append(chapter)

    book.toc = toc
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())

    epub.write_epub(output_file, book)
    print(f"\n🎉 EPUB created successfully → {output_file}")


# --------------------------------------------
# MAIN
# --------------------------------------------
def main():
    base_url = "https://freewebnovel.com/novel/tales-of-herding-gods/chapter-"
    chapter_count = 18
    output_file = "war_sovereign.epub"
    book_title = "Tales of Herding Gods – Comic Edition"

    create_epub_from_url(base_url, chapter_count, output_file, book_title)


if __name__ == "__main__":
    main()
