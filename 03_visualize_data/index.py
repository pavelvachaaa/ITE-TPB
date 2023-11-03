import re
import json
import ijson
import pandas as pd
import matplotlib.pyplot as plt
from datetime import  datetime

def split_into_smaller_parts(path: str, number_of_articles: int, parts = 5) -> None:
    """
    Funkce vezme soubour (velkýýýýý, proto ten json streamuju) a rozhodí ho do několika částí
    """

    split_when = [ *[int(number_of_articles/parts)*i for i in range(1,parts)], number_of_articles ]

    p_file = 0
    part=1

    with open(path, "rb") as file:
        print("Starting part 1")
        articles = []
        for item in ijson.items(file, "item"):
            articles.append(item)

            if part < len(split_when)+1 and p_file > split_when[part-1]:
                with open(f"part_{part}.json", "w", encoding="utf-8") as part_file:
                    json.dump(articles, part_file, indent=4, ensure_ascii=False)

                part += 1
                print(f"Starting part {part}")
                articles = []
            
            if part >= len(split_when)+1:
                break

            p_file += 1

def plot_articles_in_time(df) -> None:
    df_grouped = df.groupby(df['article_published_time'].dt.to_period('Y')).size()
    df_grouped.index = df_grouped.index.strftime('%Y-%m')

    plt.figure(figsize=(12, 6))
    plt.plot(df_grouped.index, df_grouped.values, marker='o', linestyle='-')
    plt.title("Články v čase")
    plt.xlabel("Rok publikace")
    plt.ylabel("Počet článků")
    plt.xticks(rotation=90)  

    plt.grid()
    plt.show()

def plot_bar_chart_per_year(df) -> None:
    df_grouped = df['publication_year'].value_counts().sort_index()

    plt.figure(figsize=(12, 6))
    df_grouped.plot(kind='bar', width=0.8)
    plt.title("Články v letech")
    plt.xlabel("Rok")
    plt.ylabel("Počet článků")
    plt.xticks(rotation=90)  
    plt.grid(axis='y')
    plt.tight_layout()
    plt.show()

def plot_relation_comments_length(df):

    plt.figure(figsize=(10, 6))
    plt.scatter(df['article_length'], df['article_comment_count'], alpha=0.5)
    plt.title("Závislost délky na počtu komentářů")
    plt.xlabel("Délka článku (počet slov)")
    plt.ylabel("Počet komentářů")
    plt.grid()
    plt.tight_layout()
    plt.show()

def plot_pie_chart_category(df):
    category_counts = df['article_category'].value_counts()

    plt.figure(figsize=(8, 8))
    plt.pie(category_counts, labels=category_counts.index, autopct='%1.0f%%', startangle=140)
    plt.title("Počet článků v kategorii")
    plt.axis('equal')  

    plt.show()

def plot_histogram_number_of_words(df):
    df['word_count'] = df['article_content'].apply(lambda x: len(x.split()))


    plt.figure(figsize=(10, 6))
    plt.hist(df['word_count'], bins=20, edgecolor='k')
    plt.title("Histogram počtu slov ve článku")
    plt.xlabel("Počet slov")
    plt.ylabel("Frekvence")
    plt.grid()
    plt.tight_layout()
    plt.show()

def plot_histogram_length_of_words(df):
    words = ' '.join(df['article_content']).split()
    unique_word_lengths = [len(word) for word in words]

    plt.figure(figsize=(10, 6))
    plt.hist(unique_word_lengths, bins=100, edgecolor='k', range=(0, 20)) 
    plt.title("Délka slov v článcích")
    plt.xlabel("Délka slov")
    plt.xlim(0,2500)
    plt.ylabel("")
    plt.grid()
    plt.tight_layout()
    plt.show()
    

def plot_covid_timeline(df):
    def count_word_occurrences(text, word):
        return len(re.findall(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE))

    df['covid_occurrences'] = df['article_name'].apply(lambda text: count_word_occurrences(str(text), "koronavirus"))
    df['vaccine_occurrences'] = df['article_name'].apply(lambda text: count_word_occurrences(str(text), 'vakcína'))
    

    # Oseknutí dat
    start_date = datetime(2019, 1, 1)
    end_date = datetime.now()
    df = df[(df['article_published_time'] >= start_date) & (df['article_published_time'] <= end_date)]

    df_grouped = df.groupby(df['article_published_time'].dt.to_period('M'))[['covid_occurrences', 'vaccine_occurrences']].sum()
    df_grouped.index = df_grouped.index.strftime('%Y-%m')



    plt.figure(figsize=(20, 6))
    plt.plot(df_grouped.index, df_grouped['covid_occurrences'], marker='o', linestyle='-', label='koronavirus')
    plt.plot(df_grouped.index, df_grouped['vaccine_occurrences'], marker='o', linestyle='-', label='Vakcína')
    plt.title('Výskyt kovidu a vakcín v průběhu let')
    plt.xlabel('Čas')
    plt.ylabel('Počet')
    plt.grid(False)
    plt.yticks(list(map(int, plt.yticks()[0])))
    plt.xticks(rotation=90)
    # plt.gcf().autofmt_xdate()
    plt.legend()

    plt.show()

def plot_by_weekday(df):
    articles_by_day = df['article_published_time'].dt.day_name().value_counts()
    ordered_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    # Jinak to normálně totiž začíná v neděli
    articles_by_day = articles_by_day.reindex(ordered_days)

    plt.figure(figsize=(10, 6))
    articles_by_day.plot(kind='bar', )
    plt.title("Počet článků v jednotlivých dnech v týdnu")
    plt.xlabel("Den v týdnu")
    plt.ylabel("Počet článků")
    plt.grid(axis='y')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # split_into_smaller_parts("./03_visualize_data/part_5.json", 1_400_000)
    
    with open("./part_1.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    df = pd.DataFrame(data)

    df['article_published_time'] = pd.to_datetime(df['article_published_time'])
    df['publication_year'] = df['article_published_time'].dt.year
    df['publication_month'] = df['article_published_time'].dt.month
    df['article_length'] = df['article_content'].apply(lambda x: len(x.split()))

    # plot_articles_in_time(df)
    # plot_bar_chart_per_year(df)
    # plot_relation_comments_length(df)
    # plot_pie_chart_category(df)
    # plot_histogram_number_of_words(df)
    # plot_histogram_length_of_words(df)
    # plot_covid_timeline(df)
    # plot_by_weekday(df)