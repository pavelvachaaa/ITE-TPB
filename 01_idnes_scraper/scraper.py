import re
from time import sleep
import concurrent.futures
import requests
from bs4 import BeautifulSoup
import numpy as np
from articles_util import get_client, save_urls, save_article, dump_errors, dump_urls, dump_articles, load_urls


class IdnesScraper():
    """
    Třidá zaštitujě práci se scraperem a obstarává potřebná parsování jednotlivých stránek
    """

    def __init__(self, url_index_name="idnes_urls", article_index_name="idnes_articles", num_of_threads=12):
        self.redis_url_index = url_index_name
        self.redis_article_index = article_index_name
        self.num_of_threads = num_of_threads

    def __archive_links_builder(self, start=1, end=40361):
        """
        Funkce vytvoří seznam pro scraper, kde všude se nachází odkazy na články.
        """
        return [f"https://www.idnes.cz/zpravy/archiv/{i}?datum=&idostrova=idnes" for i in range(start, end+1)]

    def __split_to_chunks(self, list_of_items: list[str], num_of_threads=12) -> list[list[str]]:
        """
        Funkce rozřadí URL pro jednotlivá vlákna
        """
        return np.array_split(list_of_items, num_of_threads)

    def parse_article(self, content: bytes) -> dict[str, any]:
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

    def parse_archive_page(self, content: bytes) -> list[str]:
        """
        Metoda vyextrahuje veškere linky z archívu a vrátí je
        [content] - response.content z requestu jako byty
        """
        soup = BeautifulSoup(content, 'html.parser')
        return [link.get('href') for link in soup.find_all(
            "a", {"class": "art-link"}) if link.get('href')]

    def process_article_chunk(self, urls: list[str]) -> list[str]:
        """
        Metoda načte stránky, vyscrapuje je a uloží do Redisu
        [returns] -> url a informaci, které failnuly
        """
        result: list[str] = []
        redis_client = get_client()
        for url in urls:
            print(f"Parsing url {url}")
            try:
                response = requests.get(url, timeout=10)
                article = self.parse_article(response.content)
                save_article(redis_client, article)
            except requests.exceptions.RequestException as e:
                print(
                    f"Most likely im ddosing the server, setting timeout for 2 mins {str(e)}")
                result.append(f"{url} timeout")
                sleep(120)
            except Exception as e:
                print(f"Exception occured at url {url} with error {str(e)}")
                result.append(
                    f"Exception occured at url {url} with error {str(e)}")

        redis_client.close()

        return result

    def process_urls_chunk(self, urls: list[str]) -> list[str]:
        """
        Metoda načte stránku archívu a extrahuje veškeré odkazy na články
        vrací url adresy, které se nepovedly
        """
        result: list[str] = []
        redis_client = get_client()
        print(f"Chunk started urls len: {len(urls)}")

        for url in urls:
            print(f"Parsing the page with index {url}")

            try:
                response = requests.get(url, timeout=10)
                links = self.parse_archive_page(response.content)
                save_urls(redis_client, links)
            except requests.exceptions.RequestException as e:
                print(
                    f"Most likely im ddosing the server, setting timeout for 2 mins {str(e)}")
                result.append(f"{url} timeout")
                sleep(120)

            sleep(0.5)

        redis_client.close()

        return result

    def run_urls_scraping(self, start=1, end=40361, output_file="idnes_urls_failed.txt"):
        """
        Metoda spustí na několika vláknech proces kradení URL adres na články
        """
        archive_links = self.__archive_links_builder(start, end)
        chunks = self.__split_to_chunks(archive_links, self.num_of_threads)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_of_threads) as executor:
            results = list(executor.map(self.process_urls_chunk, chunks))

        dump_errors(results, output_file=output_file)

    def run_article_scraping(self, urls: list[str], output_file="idnes_articles_failed.txt", ):
        """
        Metoda spustí na několika vláknech proces kradení článků
        """
        chunks = self.__split_to_chunks(urls, self.num_of_threads)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_of_threads) as executor:
            results = list(executor.map(self.process_article_chunk, chunks))

        dump_errors(results, output_file=output_file)


if __name__ == "__main__":
    SHOULD_SCRAPE_URLS = False

    scraper = IdnesScraper()
    if SHOULD_SCRAPE_URLS:
        scraper.run_urls_scraping(start=38000, end=38050)
        dump_urls()
    else:
        # Stačí mu dát libovlný pole s URL adresama...
        links_data = load_urls("idnes_urls.txt")[1:100000]
        scraper.run_article_scraping(urls=links_data)
        dump_articles()
