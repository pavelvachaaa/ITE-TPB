import json
import redis

class DataStore:
    def __init__(self, host = "localhost", port=6378, working_queue="working_queue", error_list="error_list", article_list = "data_idnes_articles", urls_list = "data_idnes_urls", articles_queue = "articles_queue", archive_queue="archive_queue"):
        self.host = host
        self.port = port
        self.working_queue = working_queue
        self.error_list = error_list
        self.article_list = article_list
        self.urls_list = urls_list
        self.articles_queue = articles_queue
        self.archive_queue = archive_queue
        self.__redis_client = self._create_redis_client()

    def _create_redis_client(self, db=0, charset="utf-8") -> redis.Redis:
        return redis.Redis(host=self.host, port=self.port, db=db, charset=charset, decode_responses=True, single_connection_client=False)

    def save_article(self, article) -> int:
       return self.__redis_client.rpush(self.article_list, json.dumps(article))
    
    def save_urls(self, urls: list[str]):
        pipeline = self.__redis_client.pipeline()
        
        for url in urls:
            pipeline.sadd(self.urls_list, url)
            pipeline.rpush(self.articles_queue, url)
        
        results = pipeline.execute()
        
        for i, url in enumerate(urls):
            if results[i] is None or results[i + 1] is None:
                raise Exception(f"Error saving URL: {url}")

    def get_url_to_scrape(self, queue: str) -> str:
        """
        [queue] = {articles_queue, archive_queue}
        """
        return self.__redis_client.brpoplpush(queue, self.working_queue, 10)
    
    def ack_scrape(self, url: str):
        self.__redis_client.lrem(self.working_queue, 0, url)

    def log_error(self, message: str) -> None:
        self.__redis_client.rpush(self.error_list,message)
        print(message)

    def generate_archive_links(self, start=1, end=40398):
        if not self.__redis_client.exists("archive_generated"):
            links = [f"https://www.idnes.cz/zpravy/archiv/{i}?datum=&idostrova=idnes" for i in range(start, end+1)]
            self.__redis_client.rpush(self.archive_queue, *links)
            self.__redis_client.set("archive_generated", "ok")

    def close(self) -> None:
        self.__redis_client.close()

    def clear(self) -> None:
        self.__redis_client.delete(*[self.working_queue, self.archive_queue, self.article_list, self.articles_queue, self.urls_list, self.error_list, "archive_generated"])

    def dump_articles(self, batch_size = 2000, output_file="idnes_articles_data.json"):
        list_length = self.__redis_client.llen(self.article_list)

        articles = []
        # Batch size, protože při velikosti dat například 1 GB už může být problém s přenosem dat.
        for i in range(0, list_length, batch_size):
            batch = self.__redis_client.lrange(self.article_list, i, i + batch_size - 1)
            for article in batch:
                json_object = json.loads(article)
                articles.append(json_object)

        with open(output_file, 'w', encoding="utf-8") as file:
            json.dump(articles, file, indent=4, ensure_ascii=False)

    def dump_urls(self,output_file="idnes_urls_data.txt") -> None:
        urls = self.__redis_client.smembers(self.urls_list)
        with open(output_file, 'w', encoding="utf-8") as file:
            file.write('\n'.join(urls))

