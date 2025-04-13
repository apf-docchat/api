import json

from flask import Blueprint, make_response, jsonify

from .helpers import ArticleDTO, get_articles_for_news_scraper, get_charts_for_news_scraper

from source.api.utilities.externalapi_helpers import auth_helper

news_scraper_api = Blueprint('news_scraper_api', __name__)


@news_scraper_api.route('/articles', methods=['GET'])
@auth_helper.token_required
def get_all_articles_for_news_scraper():
    try:
        from bson import json_util

        articles = get_articles_for_news_scraper()
        articles = json_util.dumps(articles, json_options=json_util.JSONOptions(json_mode=1))
        articles = json.loads(articles)
        articles = ArticleDTO.to_list(articles)
        return make_response(jsonify({'data': articles, 'message': 'Articles fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@news_scraper_api.route('/charts', methods=['GET'])
@auth_helper.token_required
def get_all_charts_for_news_scraper():
    try:
        charts_data = get_charts_for_news_scraper()
        return make_response(jsonify({'data': charts_data, 'message': 'Charts fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
