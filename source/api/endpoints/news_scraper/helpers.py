import os

from pymongo import MongoClient

from source.common import config


class ArticleDTO:

    def __init__(self, article):
        self._id = article.get('_id', {}).get('$oid')
        self.authors = article.get('authors')
        self.content = article.get('content')
        self.created_date = article.get('created_date', {}).get('$date')
        self.published_date = article.get('published_date', {}).get('$date')
        self.description = article.get('description')
        self.publisher = article.get('publisher')
        self.title = article.get('title')
        self.url = article.get('url')

    def to_dict(self):
        return self.__dict__

    @classmethod
    def to_list(cls, articles):
        return [cls(article).to_dict() for article in articles]


def get_articles_for_news_scraper():
    try:
        mongo_uri = config.MONGO_URI
        mongo_client = MongoClient(mongo_uri)
        db = mongo_client.get_database(os.getenv('MONGO_DATABASE'))
        articles_collection = db.get_collection("articles")  # , codec_options=codec_options)
        # articles_collection = db['articles']
        articles = articles_collection.find()
        # print(type(articles))
        if articles:
            return list(articles)
        else:
            raise RuntimeError("Articles not found!")
    except Exception as e:
        print(e)
        raise e


def get_charts_for_news_scraper():
    try:
        data = [
            {
                'title': 'Incidents by Nature of Workplace',
                'type': 'BAR_CHART',
                'data': {
                    'labels': ['Manufacturing Plants', 'Retail Stores', 'Healthcare Facilities',
                               'Educational Institutions', 'Government Offices'],
                    'data_points': [13, 4, 9, 5, 6]
                }
            },
            {
                'title': 'Incidents by Year',
                'type': 'BAR_CHART',
                'data': {
                    'labels': ['2020', '2021', '2022',
                               '2023', '2024'],
                    'data_points': [523, 652, 522, 369, 13]
                }
            }
        ]
        return data
    except Exception as e:
        print(e)
        raise e
