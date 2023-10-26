import re
import ijson
import hashlib
from datetime import datetime
from collections import Counter
from collections import defaultdict

MONTHS = [
    "Leden", "Únor", "Březen", "Duben", "Květen", "Červen",
    "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"
]


def load_stopwords(file_path = "./czech_stopwords.txt") -> list[str]:
    """
    Funkce načte seznam stopwordu ukradené z 
    https://raw.githubusercontent.com/stopwords-iso/stopwords-cs/master/stopwords-cs.txt
    """
    word_list = []
    with open(file_path, "r", encoding="utf-8") as file:
        word_list = [line.strip() for line in file] 
    
    return word_list


if __name__ == "__main__":
    stop_words = load_stopwords()
    
    filepath = "../01_idnes_scraper/idnes_articles_data.json"

    number_of_articles = 0
    number_of_comments = 0
    number_of_words = 0
    article_hashes = []


    oldest_article = None
    oldest_published_date = None

    most_commented_article = None
    most_illustrated_article = None
    
    article_categories = defaultdict(int)
    articles_per_year =  defaultdict(int)
    
    content_freq = Counter()
    month_publish_freq = Counter()

    article_with_most_words = None
    article_with_least_words = None

    top_covid_articles = []
    article_name_freq = Counter()

    with open(filepath, "rb") as file:
       for item in ijson.items(file, "item"):
            number_of_articles+=1
            article_hashes.append(hashlib.md5(str(item["article_name"]).replace(" ", "").encode()).hexdigest() )
            
            # Nalezení nejstaršího článku
            if item["article_published_time"]:
                published_date = datetime.fromisoformat(item["article_published_time"])  
                
                articles_per_year[published_date.year] += 1
                month_publish_freq[published_date.month] += 1

                if published_date.year == 2021:
                    if item["article_name"]:
                        words = re.findall(r'\w+', item["article_name"])
                        words = [word.lower() for word in words]
                        article_name_freq.update(words)

            if oldest_published_date is None or (published_date and published_date < oldest_published_date):
                    oldest_published_date = published_date
                    oldest_article = item

            # Pracování s obsahem
            if item["article_content"]:
                words = re.findall(r'\w+', item["article_content"])
                words = [word.lower() for word in words]
                words_len = len(words)
                item["content_w_length"] = words_len
                number_of_words += words_len
                content_freq.update(words) 

                if article_with_least_words is None or ( item["content_w_length"] > 10 and item["content_w_length"] < article_with_least_words["content_w_length"]):
                     article_with_least_words = item
                
                if article_with_most_words is None or item["content_w_length"] > article_with_most_words["content_w_length"]:
                     article_with_most_words = item

                covid_count = words.count("covid")
                if covid_count > 0: 
                    if len(top_covid_articles) < 3 or covid_count > top_covid_articles[-1][1]:
                        top_covid_articles.append((item, covid_count))
                        top_covid_articles.sort(key=lambda x: x[1], reverse=True)
                        top_covid_articles = top_covid_articles[:3]
        

            if item["article_category"]:
                article_categories[item["article_category"]] += 1

            # Největší počet obrázků
            if item["article_image_count"]:
                if most_illustrated_article is None or item["article_image_count"] > most_illustrated_article["article_image_count"]:
                     most_illustrated_article = item

            # Pracování s komentáři
            if item["article_comment_count"]:
                article_comment_count =  item["article_comment_count"]
                number_of_comments += article_comment_count

                if most_commented_article is None or article_comment_count > most_commented_article["article_comment_count"]:
                     most_commented_article = item

    hash_counts = Counter(article_hashes)
    collisions = [hash for hash, count in hash_counts.items() if count > 1]


    words_without_stopwords =  [(word, freq) for word, freq in content_freq.items() if word not in stop_words]

    # Nejčastejší slova kratší jak 6
    most_common = [(word, freq) for word, freq in words_without_stopwords if len(word) < 6]
    most_common.sort(key=lambda x: x[1], reverse=True)

    # Average přes všechny články bez stopwordů
    total_length = sum(len(word) for word, _ in words_without_stopwords)
    average_length = total_length / len(words_without_stopwords)

    # Publikace v měsících (předpokládám, že to bereme celkově a ne po letech)
    most_published_month, most_published_count = month_publish_freq.most_common(1)[0]
    least_published_month, least_published_count = month_publish_freq.most_common()[-1]

    article_name_freq =  [(word, freq) for word, freq in article_name_freq.items() if word not in stop_words]
    article_name_freq.sort(key=lambda x: x[1], reverse=True)
    most_common_article_names = article_name_freq[:5]


    print(f"Number of articles: {number_of_articles}")
    print(f"Number of duplicites: {len(collisions)}")
    print(f"Oldest article: {oldest_article['article_published_time']}")
    print(f"Total number of comments: {number_of_comments}")
    print(f"Total number of words: {number_of_words}")
    print(f"Most commented article: {most_commented_article["article_name"]} with {most_commented_article["article_comment_count"]} comments")
    print(f"Most illustrated article: {most_illustrated_article["article_name"]} with {most_illustrated_article["article_image_count"]} photos")
    
    print(f"Most words in article: {article_with_most_words["article_name"]} with {article_with_most_words["content_w_length"]} words")
    print(f"Most words in article: {article_with_least_words["article_name"]} with {article_with_least_words["content_w_length"]} words")

    print(f"Average length of word: {average_length}")

    print("Top three articles with the most occurrences of 'covid':")
    for i, (article, count) in enumerate(top_covid_articles):
        print(f"{i + 1}: {article['article_name']} with {count} covid-19 occurrences")

        
    print("5 most used words in article names for articles published in 2021:")
    for word, frequency in most_common_article_names:
        print(f"{word}: {frequency}")
    
    print(f"Month with the most published articles: {MONTHS[most_published_month-1]} with {most_published_count} articles.")
    print(f"Month with the least published articles: {MONTHS[least_published_month-1]} with {least_published_count} articles.")


    print("Most common words in content with < 6 words:")
    for word, frequency in most_common[:8]:
        print(f"{word}: {frequency}")

    
    for year, count in articles_per_year.items():
        print(f"Year: {year}, Number of Articles: {count}")

    # Kategorie
    print(f"Number of unique categories: {len(article_categories)}")
    for category, count in article_categories.items():
        print(f"Category: {category}, Number of Articles: {count}")

