import requests
import os
import concurrent.futures
from data_store import DataStore
from idnes_parser import parse_article, parse_archive_page
import threading
from enum import Enum
from time import sleep

class ScraperMode(Enum): 
    SCRAPE_ARCHIVE_URLS = 1
    SCRAPE_ARTICLES = 2

class IdnesScraper:

    def __init__(self, redis_host='localhost', redis_port=6379, num_of_threads=5, mode: ScraperMode = ScraperMode.SCRAPE_ARTICLES, redis_pass=""):
        self.redis_host = os.getenv('REDIS_HOST', redis_host)
        self.redis_port = int(os.getenv('REDIS_PORT', redis_port))
        self.redis_pass = os.getenv('REDIS_PASS',redis_pass)
        self.num_of_threads = int(os.getenv('NUM_OF_THREADS', num_of_threads))
        self.mode = ScraperMode(int(os.environ.get('SCRAPER_MODE', mode.value)))
        self.store = DataStore(host=self.redis_host, port=self.redis_port, password=self.redis_pass)

    def __process_urls(self) -> None:
        """
        Metoda bere URLs z queue, vyscrapuje je a uloží články do Redisu
        [returns] -> url a informaci, které failnuly
        """
        # Pro thread safety by každý thread měl mít svůj datastore
        data_store = DataStore(host=self.redis_host, port=self.redis_port, password=self.redis_pass)
        thread_id = threading.get_ident()

        if (self.mode == ScraperMode.SCRAPE_ARTICLES):
            scrape_queue = "articles_queue"
        else:
            scrape_queue = "archive_queue"

        print(f"[{thread_id}] started scraping")

        while True:
            try:
                # Načtení adresy ze scrape_queue a přesun do workinq_queue
                url = data_store.get_url_to_scrape(queue=scrape_queue)
                if "www.idnes.cz" not in url:
                    continue
                
                url.replace('/foto', '')
        
                print(f"[{thread_id}][{scrape_queue}] scrapes {url}")
                response = requests.get(str(url), timeout=10)
                if (self.mode == ScraperMode.SCRAPE_ARTICLES):
                    article = parse_article(response.content)
                    success = data_store.save_article(article)
                else:
                    archive_urls = parse_archive_page(response.content)
                    data_store.save_urls(archive_urls)
                    success = True

                # Potvrzení, že jsme úspěšně vykonali scraping
                if success:
                    data_store.ack_scrape(url)
                else: 
                    raise Exception(f"[{thread_id}] Couldn't save resource with url: {url}")
                
            except requests.exceptions.RequestException as e:
                msg = f"[{thread_id}] Most likely im ddosing the server, setting timeout for 2 mins {str(e)}"
                data_store = data_store.log_error(msg)
                sleep(120)
                continue
            except Exception as e:
                msg = f"[{thread_id}] Exception occured at url {url} with error {str(e)}"
                data_store = data_store.log_error(msg)
                continue


    def generate_archive(self,start=1, end=40398):
        self.store.generate_archive_links(start, end)

    def clear(self):
        self.store.clear()

    def dump_data(self,type="articles"):
        if type == "articles":
            self.store.dump_articles()
        else:
            self.store.dump_urls()
        
    def run(self):
        """
        Metoda spustí na několika vláknech proces kradení URL adres na články nebo proces kradení článků
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_of_threads) as executor:
            for _ in range(self.num_of_threads):
                executor.submit(self.__process_urls)
              
        executor.shutdown(wait=True)

        print("Scraping of articles is done, no more urls in queue, Im shuting down")

if __name__ == "__main__": 
    scraper = IdnesScraper(redis_host='20.109.19.66', redis_port=6379, mode=ScraperMode.SCRAPE_ARCHIVE_URLS, num_of_threads=8, redis_pass="")
    # scraper.clear()
    scraper.generate_archive()
    scraper.run()
    # scraper.dump_data()