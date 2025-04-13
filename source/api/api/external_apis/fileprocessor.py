from flask import Blueprint, jsonify, request, make_response
from source.api.utilities.externalapi_helpers import auth_helper, docguide_helper, fileprocessor_helper

fileprocessor = Blueprint('fileprocessor', __name__)


@fileprocessor.route('/custom-instruction', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_custom_instruction():
    try:
        custom_instruction = fileprocessor_helper.get_custom_instruction_helper()
        return make_response(
            jsonify({'data': custom_instruction, 'message': 'Custom instruction fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/custom-instruction', methods=['PUT'])
@auth_helper.token_required
#@auth_helper.authorised
def update_custom_instruction():
    try:
        fileprocessor_helper.update_custom_instruction_helper()
        return make_response(
            jsonify({'message': 'Custom instruction updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@fileprocessor.route('/custom-instruction-generate', methods=['POST'])
@auth_helper.token_required
#@auth_helper.authorised
def custom_instruction_generate():
    try:
        custom_instructions = fileprocessor_helper.generate_custom_instructions()
        return make_response(jsonify({'message': 'Custom Instructions generated!', 'data': custom_instructions}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_metadata_content():
    try:
        # request.context['content_type'] = 'metadata'
        metadata_status = fileprocessor_helper.get_docchat_metadata_files()
        return make_response(
            jsonify({'data': metadata_status, 'message': 'Metadata content fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata/status', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_metadata_status():
    try:
        request.context['status_type'] = 'metadata'
        metadata_status = fileprocessor_helper.get_fileprocessor_status_helper()
        return make_response(
            jsonify({'data': metadata_status, 'message': 'Metadata status fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata/update', methods=['POST'])
@auth_helper.token_required
#@auth_helper.authorised
def metadata_update():
    try:
        response_message = fileprocessor_helper.process_docchat_metadata()
        return make_response(jsonify({'message': response_message}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata/download', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def metadata_metadata_download():
    try:
        # request.context['status_type'] = 'metadata'
        metadata = fileprocessor_helper.get_docchat_metadata_for_download()
        return make_response(
            jsonify({'data': metadata, 'message': 'Metadata fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/summarise', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_summarise_content():
    try:
        request.context['content_type'] = 'summarise'
        metadata_status = fileprocessor_helper.get_fileprocessor_content()
        return make_response(
            jsonify({'data': metadata_status, 'message': 'Summarise content fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/summarise/status', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_summarise_status():
    try:
        request.context['status_type'] = 'summarise'
        summarise_status = fileprocessor_helper.get_fileprocessor_status_helper()
        return make_response(
            jsonify({'data': summarise_status, 'message': 'Summarise status fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/summarise/update', methods=['POST'])
@auth_helper.token_required
#@auth_helper.authorised
def summarise_update():
    try:
        doc_summaries = fileprocessor_helper.fileprocessor_summarise_update()
        return make_response(
            jsonify({'data': doc_summaries, 'message': 'Summarise updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/summarise/download', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def summarise_metadata_download():
    try:
        request.context['status_type'] = 'summarise'
        metadata = fileprocessor_helper.get_metadata_for_download()
        return make_response(
            jsonify({'data': metadata, 'message': 'Metadata fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/doc-guide/process-file', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised
def file_processor_docguide_process_file():
    try:
        docguide_helper.file_process()
        return make_response(
            jsonify({'message': 'File processed successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/doc-guide/process-file', methods=['DELETE'])
@auth_helper.token_required
@auth_helper.authorised
def file_processor_docguide_delete_file():
    try:
        docguide_helper.docguide_delete_files()
        return make_response(
            jsonify({'message': 'Files deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/faq', methods=['POST'])
@auth_helper.token_required
#@auth_helper.authorised
def create_docchat_faq():
    try:
        fileprocessor_helper.create_docchat_faq()
        return make_response(
            jsonify({'message': 'Faq created successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/faq', methods=['PATCH'])
@auth_helper.token_required
#@auth_helper.authorised
def update_docchat_faq():
    try:
        fileprocessor_helper.update_docchat_faq()
        return make_response(
            jsonify({'message': 'Faq updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/faq', methods=['DELETE'])
@auth_helper.token_required
#@auth_helper.authorised
def delete_docchat_faq():
    try:
        fileprocessor_helper.delete_docchat_faq()
        return make_response(
            jsonify({'message': 'Faq deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/faq', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_docchat_faq():
    try:
        faqs = fileprocessor_helper.get_docchat_faq()
        return make_response(
            jsonify({'data': faqs, 'message': 'Faq fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/faq/download', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_docchat_faq_for_download():
    try:
        faqs = fileprocessor_helper.get_docchat_faq()
        return make_response(
            jsonify({'data': faqs, 'message': 'Faq fetched for download successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata-schema', methods=['POST'])
@auth_helper.token_required
#@auth_helper.authorised
def save_metadata_schema():
    try:
        fileprocessor_helper.save_metadata_schema()
        return make_response(jsonify({'message': 'Metadata schema saved and processed its metadata successfully!'}),
                             200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@fileprocessor.route('/metadata-schema-generate', methods=['POST'])
@auth_helper.token_required
#@auth_helper.authorised
def save_metadata_schema_generate():
    try:
        fileprocessor_helper.generate_metadata_schema()
        return make_response(jsonify({'message': 'Metadata schema generated!'}),
                             200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@fileprocessor.route('/metadata-schema', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_metadata_schema():
    try:
        metadata_content = fileprocessor_helper.get_metadata_schema()
        return make_response(jsonify({'data': metadata_content, 'message': 'Metadata schema fetched successfully!'}),
                             200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata-schema', methods=['PATCH'])
@auth_helper.token_required
#@auth_helper.authorised
def update_metadata_schema():
    try:
        fileprocessor_helper.update_metadata_schema()
        return make_response(jsonify({'message': 'Metadata schema updated and reprocessed its metadata successfully!'}),
                             200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata-schema/weight', methods=['PATCH'])
@auth_helper.token_required
#@auth_helper.authorised
def update_metadata_schema_weight():
    try:
        fileprocessor_helper.update_metadata_schema_weight()
        return make_response(jsonify({'message': 'Metadata schema updated and reprocessed its metadata successfully!'}),
                             200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata-schema', methods=['DELETE'])
@auth_helper.token_required
#@auth_helper.authorised
def delete_metadata_schema():
    try:
        fileprocessor_helper.delete_metadata_schema()
        return make_response(jsonify({'message': 'Metadata schema deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/metadata/upload', methods=['POST'])
@auth_helper.token_required
#@auth_helper.authorised
def upload_metadata_file():
    try:
        fileprocessor_helper.upload_metadata_file()
        return make_response(jsonify({'message': 'File metadata updated successfully!'}), 200)
    except Exception as e:
        return make_response(jsonify({'message': str(e)}), 500)


@fileprocessor.route('/collection-rule', methods=['PUT'])
@auth_helper.token_required
@auth_helper.authorised
def save_collection_rule():
    try:
        fileprocessor_helper.save_collection_rule()
        return make_response(jsonify({'message': 'Collection rule saved successfully!'}),
                             200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@fileprocessor.route('/collection-rule', methods=['GET'])
@auth_helper.token_required
#@auth_helper.authorised
def get_collection_rule():
    try:
        collection_rules = fileprocessor_helper.get_collection_rule()
        return make_response(jsonify({'data': collection_rules, 'message': 'Collection rule fetched successfully!'}),
                             200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
