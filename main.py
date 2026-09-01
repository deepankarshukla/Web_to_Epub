import time
import uuid
import html
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib3
from bs4 import BeautifulSoup
from ebooklib import epub

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_THREADS = 10
REQUEST_DELAY = 6
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3

START_CHAPTER = 1
END_CHAPTER = 1840

BASE_URL = (
    "https://freewebnovel.com/novel/tales-of-herding-gods/chapter-"
)

OUTPUT_FILE = "tale_of_herding_god.epub"

BOOK_TITLE = "Tales of Herding Gods"
BOOK_AUTHOR = "Unknown"

# Optional
BOOK_DESCRIPTION = """
A complete collection of Tales of Herding Gods chapters,
formatted as a comfortable EPUB reading experience.
"""


# ============================================================
# EPUB CSS
# ============================================================

BOOK_CSS = """

/* =========================================================
   General page
   ========================================================= */

body {
    margin: 5%;
    padding: 0;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.65;
    text-align: justify;
    color: #222222;
}

/* =========================================================
   Chapter
   ========================================================= */

.chapter-container {
    margin: 0 auto;
    max-width: 42em;
}

.chapter-number {
    margin-top: 2em;
    margin-bottom: 0.3em;
    text-align: center;
    font-family: Georgia, serif;
    font-size: 0.85em;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #777777;
}

.chapter-title {
    margin-top: 0;
    margin-bottom: 1.5em;
    text-align: center;
    font-family: Georgia, serif;
    font-size: 1.8em;
    line-height: 1.25;
    font-weight: bold;
}

.chapter-divider {
    width: 35%;
    margin: 1.5em auto 2em auto;
    text-align: center;
    color: #888888;
    font-size: 1.2em;
}

.chapter-divider::before {
    content: "✦  ✦  ✦";
}

/* =========================================================
   Paragraphs
   ========================================================= */

.chapter-container p {
    margin-top: 0;
    margin-bottom: 0.85em;
    text-indent: 1.4em;
}

/*
 * First paragraph after a heading doesn't need indentation.
 */

.chapter-container h1 + p,
.chapter-container h2 + p,
.chapter-container .chapter-divider + p {
    text-indent: 0;
}

/* =========================================================
   Drop cap
   ========================================================= */

.drop-cap:first-letter {
    float: left;
    font-size: 3.2em;
    line-height: 0.8;
    padding-right: 0.08em;
    padding-top: 0.08em;
    font-weight: bold;
}

/* =========================================================
   Sub-headings
   ========================================================= */

.chapter-container h2 {
    margin-top: 2em;
    margin-bottom: 1em;
    text-align: center;
    font-size: 1.25em;
}

/* =========================================================
   Quotes
   ========================================================= */

.chapter-container blockquote {
    margin: 1.5em 1.5em;
    padding-left: 1em;
    border-left: 3px solid #cccccc;
    color: #555555;
    font-style: italic;
}

/* =========================================================
   Images
   ========================================================= */

.chapter-container img {
    display: block;
    max-width: 100%;
    height: auto;
    margin: 1.5em auto;
}

/* =========================================================
   Chapter navigation
   ========================================================= */

.chapter-navigation {
    margin-top: 4em;
    padding-top: 1.5em;
    border-top: 1px solid #cccccc;
    text-align: center;
    font-family: Georgia, serif;
}

.chapter-navigation a {
    text-decoration: none;
    font-weight: bold;
}

.nav-separator {
    padding: 0 1em;
    color: #999999;
}

/* =========================================================
   Title page
   ========================================================= */

.title-page {
    text-align: center;
    margin-top: 25%;
}

.title-page h1 {
    font-size: 2.5em;
    line-height: 1.2;
    margin-bottom: 0.5em;
}

.title-page .subtitle {
    font-size: 1.1em;
    color: #777777;
    margin-bottom: 3em;
}

.title-page .ornament {
    font-size: 1.5em;
    margin: 2em 0;
}

/* =========================================================
   Copyright / information page
   ========================================================= */

.info-page {
    margin-top: 10%;
    text-align: center;
    color: #666666;
}

.info-page p {
    text-indent: 0;
    margin-bottom: 1em;
}

/* =========================================================
   Back to contents
   ========================================================= */

.toc-link {
    margin-top: 3em;
    text-align: center;
}

.toc-link a {
    text-decoration: none;
    font-size: 0.9em;
}

"""


# ============================================================
# HTTP SESSION
# ============================================================

def create_session():
    """
    Create a requests session with browser-like headers.
    """

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/139.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })

    return session


# ============================================================
# CLEAN HTML
# ============================================================

def clean_content(content):
    """
    Clean scraped chapter HTML so that it looks like an actual novel.
    """

    # Remove unwanted elements
    for element in content.find_all([
        "script",
        "style",
        "iframe",
        "form",
        "button",
        "noscript"
    ]):
        element.decompose()

    # Remove empty paragraphs
    for p in content.find_all("p"):
        text = p.get_text(" ", strip=True)

        if not text:
            p.decompose()
            continue

        # Remove excessive whitespace
        text = " ".join(text.split())

        p.clear()
        p.string = text

    # Remove excessive <br>
    for br in content.find_all("br"):
        br.replace_with(" ")

    return content


# ============================================================
# FETCH ONE CHAPTER
# ============================================================

def fetch_chapter(chapter_number):
    """
    Download and parse one chapter.
    """

    url = f"{BASE_URL}{chapter_number}"

    session = create_session()

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                verify=False
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.content,
                "html.parser"
            )

            # ------------------------------------------------
            # Chapter title
            # ------------------------------------------------

            title_element = soup.find(
                "span",
                class_="chapter"
            )

            if title_element:
                title = title_element.get_text(" ",
                    strip=True
                )
            else:
                title = f"Chapter {chapter_number}"

            # ------------------------------------------------
            # Chapter content
            # ------------------------------------------------

            content = soup.find(
                "div",
                id="article"
            )

            if content is None:

                print(
                    f"⚠️ Chapter {chapter_number}: "
                    f"content not found"
                )

                return None

            content = clean_content(content)

            # ------------------------------------------------
            # Convert first paragraph to drop-cap paragraph
            # ------------------------------------------------

            first_paragraph = content.find("p")

            if first_paragraph:

                classes = first_paragraph.get(
                    "class",
                    []
                )

                classes.append("drop-cap")

                first_paragraph["class"] = classes

            print(
                f"✅ Chapter {chapter_number}: {title}"
            )

            # Keep requested delay
            time.sleep(REQUEST_DELAY)

            return {
                "number": chapter_number,
                "title": title,
                "content": str(content)
            }

        except Exception as e:

            print(
                f"⚠️ Chapter {chapter_number} "
                f"attempt {attempt}/{MAX_RETRIES}: {e}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(2)

    print(
        f"❌ Failed permanently: Chapter "
        f"{chapter_number}"
    )

    return None


# ============================================================
# TITLE PAGE
# ============================================================

def create_title_page(book):

    title_page = epub.EpubHtml(
        title="Title Page",
        file_name="title.xhtml",
        lang="en"
    )

    title_page.content = f"""
    <html>
    <head>
        <title>{html.escape(BOOK_TITLE)}</title>
    </head>

    <body>

        <div class="title-page">

            <div class="ornament">
                ❖
            </div>

            <h1>
                {html.escape(BOOK_TITLE)}
            </h1>

            <p class="subtitle">
                {html.escape(BOOK_AUTHOR)}
            </p>

            <div class="ornament">
                ✦ &nbsp; ✦ &nbsp; ✦
            </div>

            <p>
                {html.escape(BOOK_DESCRIPTION.strip())}
            </p>

        </div>

    </body>
    </html>
    """

    book.add_item(title_page)

    return title_page


# ============================================================
# INFORMATION PAGE
# ============================================================

def create_info_page(book):

    info_page = epub.EpubHtml(
        title="About This Edition",
        file_name="about.xhtml",
        lang="en"
    )

    info_page.content = f"""
    <html>
    <head>
        <title>About This Edition</title>
    </head>

    <body>

        <div class="info-page">

            <h1>About This Edition</h1>

            <div class="chapter-divider"></div>

            <p>
                <strong>{html.escape(BOOK_TITLE)}</strong>
            </p>

            <p>
                This EPUB edition has been formatted
                for comfortable reading on phones,
                tablets and e-readers.
            </p>

            <p>
                Chapters are arranged in numerical order
                and include navigation between chapters.
            </p>

            <p>
                Source:
                {html.escape(BASE_URL)}
            </p>

        </div>

    </body>
    </html>
    """

    book.add_item(info_page)

    return info_page


# ============================================================
# CREATE CHAPTER
# ============================================================

def create_chapter(
    book,
    chapter_data,
    previous_chapter=None,
    next_chapter=None
):

    number = chapter_data["number"]
    title = chapter_data["title"]
    content = chapter_data["content"]

    filename = f"chap_{number}.xhtml"

    chapter = epub.EpubHtml(
        title=title,
        file_name=filename,
        lang="en"
    )

    previous_link = ""

    if previous_chapter:
        previous_link = f"""
        <a href="chap_{previous_chapter}.xhtml">
            ← Previous
        </a>
        """

    next_link = ""

    if next_chapter:
        next_link = f"""
        <a href="chap_{next_chapter}.xhtml">
            Next →
        </a>
        """

    navigation = f"""
    <div class="chapter-navigation">

        {previous_link}

        <span class="nav-separator">•</span>

        <a href="nav.xhtml">
            Contents
        </a>

        <span class="nav-separator">•</span>

        {next_link}

    </div>
    """

    chapter.content = f"""
    <html>

    <head>
        <title>{html.escape(title)}</title>
    </head>

    <body>

        <div class="chapter-container">

            <div class="chapter-number">
                Chapter {number}
            </div>

            <h1 class="chapter-title">
                {html.escape(title)}
            </h1>

            <div class="chapter-divider"></div>

            {content}

            {navigation}

        </div>

    </body>

    </html>
    """

    book.add_item(chapter)

    return chapter


# ============================================================
# CREATE EPUB
# ============================================================

def create_epub(
    chapters_data,
    output_file
):

    print("\n📚 Building EPUB...\n")

    book = epub.EpubBook()

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    book.set_identifier(
        str(uuid.uuid4())
    )

    book.set_title(
        BOOK_TITLE
    )

    book.set_language(
        "en"
    )

    book.add_author(
        BOOK_AUTHOR
    )

    book.add_metadata(
        "DC",
        "description",
        BOOK_DESCRIPTION
    )

    book.add_metadata(
        "DC",
        "subject",
        "Fantasy Fiction"
    )

    book.add_metadata(
        "DC",
        "publisher",
        "Personal EPUB Edition"
    )

    # --------------------------------------------------------
    # CSS
    # --------------------------------------------------------

    style = epub.EpubItem(
        uid="style",
        file_name="style/book.css",
        media_type="text/css",
        content=BOOK_CSS.encode("utf-8")
    )

    book.add_item(style)

    # --------------------------------------------------------
    # Title page
    # --------------------------------------------------------

    title_page = create_title_page(book)

    # --------------------------------------------------------
    # Information page
    # --------------------------------------------------------

    info_page = create_info_page(book)

    # --------------------------------------------------------
    # Chapters
    # --------------------------------------------------------

    chapters = []

    for index, chapter_data in enumerate(chapters_data):

        previous_chapter = None

        next_chapter = None

        if index > 0:
            previous_chapter = chapters_data[
                index - 1
            ]["number"]

        if index < len(chapters_data) - 1:
            next_chapter = chapters_data[
                index + 1
            ]["number"]

        chapter = create_chapter(
            book,
            chapter_data,
            previous_chapter,
            next_chapter
        )

        chapters.append(chapter)

    # --------------------------------------------------------
    # Table of contents
    # --------------------------------------------------------

    book.toc = [
        title_page,
        info_page,
        epub.Section("Chapters"),
        *chapters
    ]

    # --------------------------------------------------------
    # Navigation
    # --------------------------------------------------------

    nav = epub.EpubNav()

    book.add_item(nav)

    # NCX for older readers
    ncx = epub.EpubNcx()

    book.add_item(ncx)

    # --------------------------------------------------------
    # Spine
    # --------------------------------------------------------

    book.spine = [
        "nav",
        title_page,
        info_page,
        *chapters
    ]

    # --------------------------------------------------------
    # Write EPUB
    # --------------------------------------------------------

    epub.write_epub(
        output_file,
        book,
        {}
    )

    print(
        f"\n🎉 EPUB successfully created!"
    )

    print(
        f"📖 Book      : {BOOK_TITLE}"
    )

    print(
        f"📚 Chapters  : {len(chapters)}"
    )

    print(
        f"📁 File      : {output_file}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        f"📚 {BOOK_TITLE}"
    )

    print("=" * 60)

    print(
        f"Downloading chapters "
        f"{START_CHAPTER} → {END_CHAPTER}"
    )

    chapter_numbers = range(
        START_CHAPTER,
        END_CHAPTER + 1
    )

    chapters_data = []

    # --------------------------------------------------------
    # Download concurrently
    # --------------------------------------------------------

    with ThreadPoolExecutor(
        max_workers=MAX_THREADS
    ) as executor:

        futures = {
            executor.submit(
                fetch_chapter,
                chapter_number
            ): chapter_number
            for chapter_number in chapter_numbers
        }

        completed = 0

        total = len(futures)

        for future in as_completed(futures):

            chapter_number = futures[future]

            try:

                result = future.result()

                if result:

                    chapters_data.append(
                        result
                    )

            except Exception as e:

                print(
                    f"❌ Chapter {chapter_number}: {e}"
                )

            completed += 1

            print(
                f"Progress: "
                f"{completed}/{total}"
            )

    # --------------------------------------------------------
    # Sort chapters
    # --------------------------------------------------------

    chapters_data.sort(
        key=lambda x: x["number"]
    )

    if not chapters_data:

        print(
            "\n❌ No chapters downloaded."
        )

        return

    # --------------------------------------------------------
    # Create EPUB
    # --------------------------------------------------------

    create_epub(
        chapters_data,
        OUTPUT_FILE
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()