
from flask import Blueprint, jsonify, make_response, current_app

from source.api.utilities.externalapi_helpers.webhook_helper import WebhookHelper

webhooks = Blueprint('webhook_route', __name__)


@webhooks.route('/whatsapp/callback', methods=['GET'])
def verify_whatsapp():
    try:
        result = WebhookHelper().verify_whatsapp()
        current_app.logger.info(f"webhook_helper.verify_whatsapp result: {result}, type: {type(result)}")
        return make_response(result, 200)
    except Exception as e:
        return make_response(jsonify({'message': str(e)}), 500)


@webhooks.route('/whatsapp/callback', methods=['POST'])
def handle_whatsapp():
    try:
        WebhookHelper().handle_whatsapp()
        return make_response(jsonify({'message': 'Webhook handled successfully!'}), 200)
    except Exception as e:
        return make_response(jsonify({'message': str(e)}), 500)
