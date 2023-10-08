import json
import redis


def get_client(host='localhost', port=6379, db=0, charset="utf-8") -> redis.Redis:
    """
    Redis automaticky na pozadí vytváří connection pool
    """
    return redis.Redis(host=host, port=port, db=db, charset=charset, decode_responses=True, single_connection_client=False)


def dump_errors(lines: list[list[str]], output_file="idnes_urls_failed.txt") -> None:
    """
    Funkce ukládá nepovedené výsledky
    """
    failed_links = set()
    for chunk_result in lines:
        failed_links.update(chunk_result)

    with open(output_file, 'w', encoding="utf-8") as file:
        file.write('\n'.join(failed_links))


def dump_urls(output_file="idnes_urls.txt") -> None:
    """
    Funkce vezme list adres a uloží ho do souboru
    """
    urls = load_urls("redis")
    with open(output_file, 'w', encoding="utf-8") as file:
        file.write('\n'.join(urls))


def dump_articles(output_file="idnes_articles.json") -> None:
    """
    Funkce načte seznam článků z redisu a uloží ho jako JSON
    """
    articles = load_articles()
    with open(output_file, 'w', encoding="utf-8") as file:
        json.dump(articles, file, indent=4, ensure_ascii=False)


def save_urls(redis_client: redis.Redis, urls: list[str], index="idnes_urls") -> None:
    """
    Funkce ukládá seznam url adres článku do Redisu
    """
    redis_client.sadd(index, *urls)


def save_article(redis_client: redis.Redis, article: dict[str, any], index="idnes_articles") -> None:
    """
    Funkce ukládá článek do Redisu
    """
    redis_client.rpush(index, json.dumps(article))


def load_urls(data_source="redis", index="idnes_urls") -> list[str]:
    """
    Funkce podle data_source načte url adresy článků
    """

    urls: list[str] = []
    if (data_source == "redis"):
        urls = __load_urls_from_redis(index)
    else:
        urls = __load_urls_from_txt(data_source)

    # Nechceme otevírat galerie a chceme jen idnes.cz
    return [url.replace('/foto', '')
            for url in urls if "www.idnes.cz" in url]


def load_articles(index="idnes_articles") -> list[dict[str, any]]:
    """
    Funkce načte veškeré články z redisu do listu
    """
    articles = get_client().lrange(index, 0, -1)
    return [json.loads(json_string,) for json_string in articles]


def __load_urls_from_txt(file_name) -> list[str]:
    urls: list[str] = []
    with open(file_name, 'r', encoding="utf-8") as file:
        urls = file.readlines()

    return [line.strip() for line in urls]


def __load_urls_from_redis(index="idnes_urls") -> list[str]:
    """
    Funkce načte z neseřazené množiny všechny URL adresy a vrátí je
    """
    redis_client = get_client()
    return redis_client.smembers(index)
