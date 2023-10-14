# Cvičení 01 - idnes.cz scraper

Pro uložení informací byl využit redis (ukládání mezivýsledků v případě chyb a kvůli rychlosti ukládání). 

## Spuštění
Redis můžete spustit pomocí příkazu:

```bash
sudo docker run --rm --name some-redis -d  -p 6379:6379 -v ~/projects/scraper/data:/data redis redis-server --save 60 --loglevel warning
```

`--save 60 1000` nám zajištuje to, že každých 60 sekund se to uloží persistentně na disk, pokud se změnil alespoň jeden klíč

Samotný scraper má několik možností spuštění
* ENV variables
* prosté spuštění v mainu s nastavením parametrů

Díky implementaci je možné spustit více instancí scraperů na více strojích a vše zůstane konzistentní

Env variables:
`SCRAPER_MODE = 1` je pro získávání adres z archívu, `SCRPAER_MODE = 2` scrapuje data z článků. Příklad spuštění

```bash
REDIS_HOST=localhost NUM_OF_THREADS=4 SCRAPER_MODE=2 python index.py
```

Prosté spuštění:
```python
if __name__ == "__main__": 
    scraper = IdnesScraper(redis_host='localhost', redis_port=6379, mode=ScraperMode.SCRAPE_ARTICLES)
    # scraper.clear()
    scraper.generate_archive()
    scraper.run()
    # scraper.dump_data()
```


## Architektura - distribuovaný scraping
Pro zajištění maximální efektivity můžeme použít vhodných datových struktur v redisu, které mají možnost se chovat atomicky.

```bash
# Pushneme do fronty URL ke scrapování a můžeme ji přiřadit případně metadata
RPUSH task_queue "https://example.com/page1 server:1"
```

V naších instanci scraperu, pak můžeme udělat pouze jen něco jako
```bash
# atomický POP z task_queue a přesun do working_queue
BRPOPLPUSH task_queue working_queue 0
```

Do `working_queue` to přesouváme kvůli zachování konzistence a kvůli fault tolerance. Kdyby consumer (scraper) udělal chybu (spadnul/špatně načetl data), tak nám nezmizí data, protože consumer bude potvrzovat, že úspěšně vykonal svou činnost.

## Requirements

`pip install beautifulsoup4 requests redis`


## Improvements
- [ ] Byla by potřeba implementovat změna adresy při timeoutu. - Free proxies 


