import re
from bs4 import BeautifulSoup

def parse_article( content: bytes) -> dict[str, any]:
        """
        Metoda vyextrahuje důležité informace o článku a vrátí je jako mapu
        [content] - response.content z requestu jako byty
        """
        soup = BeautifulSoup(content, 'html.parser')

        article_name_elem = soup.find('h1', itemprop="name headline")
        article_opener_elem = soup.find("div", class_="opener")

        content_raw = soup.find("div", id="art-text").find_all("p")
        article_content = ''.join(
            [c.string for c in content_raw if c.string is not None])

        # Počet komentářů
        comment_count_raw = soup.find("a", id="moot-linkin")
        if comment_count_raw:
            comment_count_raw = comment_count_raw.find("span")

        article_comment_count = int(re.search(
            r"\d+", comment_count_raw.string).group()) if comment_count_raw else 0

        # Meta tagy
        article_published_time = soup.find(
            "meta", {"property": "article:published_time"})
        article_author_tag = soup.find("meta", {"property": "article:author"})
        article_author = []
        if article_author_tag:
            author_value = article_author_tag['content']
            article_author = author_value.split(
                ', ') if ',' in author_value else [author_value]

        # Galerie
        article_image_count = 0
        gallery_raw = soup.find(class_="more-gallery")
        if (gallery_raw):
            article_image_count = gallery_raw.get_text()
            article_image_count = int(
                re.search(r"\d+", article_image_count).group())

        # Když je na stránce jedna fotka, tak není v more-gallery, takže ji musíme přičíst
        opener_foto_elements = soup.find_all(class_='opener-foto')
        if opener_foto_elements:
            article_image_count += len(opener_foto_elements)

        # Témata
        meta_keywords = soup.find('meta', {'name': 'keywords', 'lang': 'cs'})
        article_keywords = []
        if meta_keywords:
            content_value = meta_keywords['content']
            article_keywords = content_value.split(
                ', ') if ',' in content_value else [content_value]

        # Hledáme script tag, kde jsou Unidata - máme tam sekci a podsekci a jestli je to premium
        script_tag = soup.find('script', text=re.compile(r'var Unidata = {'))
        javascript_code = script_tag.string
        section_match = re.search(r'"section": "(.*?)",', javascript_code)
        subsection_match = re.search(
            r'"subSection": "(.*?)",', javascript_code)
        article_type_match = re.search(
            r'"articleType": "(.*?)",', javascript_code)

        section = section_match.group(1) if section_match else None
        subsection = subsection_match.group(1) if subsection_match else None
        article_type = article_type_match.group(
            1) if article_type_match else None

        article_category = f"{section} > {subsection}" if section and subsection else section or subsection
        article_is_premium = article_type == "premium"

        return {
            "article_name": article_name_elem.string if article_name_elem else "",
            "article_opener": article_opener_elem.string if article_opener_elem else "",
            "article_published_time": article_published_time["content"] if article_published_time else "",
            "article_comment_count": article_comment_count,
            "article_content": article_content,
            "article_image_count": article_image_count,
            "article_author": article_author,
            "article_keywords": article_keywords,
            "article_category": article_category,
            "article_is_premium": article_is_premium
        }

def parse_archive_page(content: bytes) -> list[str]:
    """
    Metoda vyextrahuje veškere linky z archívu a vrátí je
    [content] - response.content z requestu jako byty
    """
    soup = BeautifulSoup(content, 'html.parser')
    return [link.get('href') for link in soup.find_all(
        "a", {"class": "art-link"}) if link.get('href')]