from pymongo import MongoClient

def get_database():
   client = MongoClient("localhost", 27017)
   return client["scraper"]
  
if __name__ == "__main__":   
  
    db = get_database()
    articles = db["articles"]

    # Najděte jeden náhodný článek
    random_article = list(articles.aggregate([{ "$sample": { "size": 1 } }]))
    print(random_article)

    number_of_articles = db.command("collstats", "articles")["count"]
    print(f"Počet článků: {number_of_articles}")

    average_photos = list(articles.aggregate([{ "$group": { "_id": None, "average_image_count": {"$avg": "$article_image_count"} } }]))
    print(f"Průměrný počet článků: {average_photos}")
    
    photos_gt_100 = articles.count_documents({"article_comment_count": {"$gt": 100}})
    print(f"Počet článku, kde komentáře > 100: {photos_gt_100}")

    grouped_categories = list(db.articles.aggregate([
        {
            "$match": {
                "article_published_time": {
                    "$gte": "2022-01-01T00:00:00Z",
                    "$lt": "2023-01-01T00:00:00Z"
                }
            }
        },
        {
            "$group": {
                "_id": "$article_category",
                "count": {"$sum": 1}
            }
        }
    ]))

    print(grouped_categories)