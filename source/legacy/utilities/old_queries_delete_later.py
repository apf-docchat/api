# USER RELATED QUERIES
FIND_USER_BY_USERNAME = "SELECT id, password_hash FROM users WHERE username = %s"
FIND_USER_BY_EMAIL = "SELECT * FROM users WHERE email = %s"
FIND_USER_BY_USER_ID = "SELECT * FROM users WHERE id = %s"

# ORGANIZATION RELATED QUERIES
FIND_ORGANIZATION_BY_USER_ID = """
            SELECT o.org_id, o.org_name
            FROM organization o
            JOIN user_organization uo ON o.org_id = uo.org_id
            JOIN users u ON u.id = uo.user_id
            WHERE u.id = %s
            """
FIND_ORGANIZATION_BY_ORGANIZATION_ID = """
            SELECT *
            FROM organization o
            WHERE o.org_id = %s
            """
FIND_USER_ORGANIZATION_BY_ORGANIZATION_ID_AND_USER_ID = '''
            SELECT * 
            FROM user_organization
            WHERE org_id = %s 
            AND user_id = %s 
            '''

# MODULE RELATED QUERIES
FIND_MODULES_BY_ORGANIZATION_ID = """
            SELECT m.id, m.button_text, m.name, m.description
            FROM organization_modules om
            JOIN modules m ON om.module_id = m.id
            WHERE om.org_id = %s
            """
FIND_ALL_MODULES = """
            SELECT *
            FROM modules
            """

# FILES RELATED QUERIES
FIND_FILES_BY_ORGANIZATION_ID = """
            SELECT f.file_id, f.file_name, c.collection_name, c.collection_id  
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN collections c ON fc.collection_id = c.collection_id
            JOIN organization_collections oc ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s
            """
FIND_FILES_BY_COLLECTION_IDS = """
            SELECT f.file_id, f.file_name, fc.collection_id, f.upload_datetime
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            WHERE fc.collection_id IN %s
            ORDER BY f.upload_datetime DESC
            """
FIND_FILES_WITH_DOCGUIDE_FILES_BY_COLLECTION_IDS = """
            SELECT f.file_id, f.file_name, fc.collection_id
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN docguide_files df ON f.file_id = df.doc_file_id
            WHERE fc.collection_id IN %s
            """
FIND_FILES_BY_FILES_IDS = query = """
            SELECT *
            FROM files f
            WHERE f.file_id IN %s
            """
FIND_FILES_COUNT_BY_COLLECTION_ID_AND_ORGANIZATION_ID = """
            SELECT COUNT(*) AS total
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            JOIN collections c ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND c.collection_id = %s
            """
FIND_FILES_COUNT_OF_METADATA_BY_COLLECTION_ID_AND_ORGANIZATION_ID = """
            SELECT COUNT(*) AS total
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            JOIN collections c ON c.collection_id = oc.collection_id
            JOIN files_metadata fm ON fm.file_id = f.file_id
            WHERE oc.org_id = %s AND c.collection_id = %s
            """
FIND_FILES_COUNT_OF_METADATA_PLUS_BY_COLLECTION_ID_AND_ORGANIZATION_ID = """
            SELECT COUNT(*) AS total
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            JOIN collections c ON c.collection_id = oc.collection_id
            JOIN files_metadata_plus fmp ON fmp.file_id = f.file_id
            WHERE oc.org_id = %s AND c.collection_id = %s
            """
FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT *
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN collections c ON fc.collection_id = c.collection_id
            JOIN organization_collections oc ON c.collection_id = oc.collection_id
            WHERE c.collection_id = %s AND oc.org_id = %s
            """
FIND_FILES_FOR_METADATA_PLUS_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT DISTINCT f.file_id
            FROM files f
            JOIN files_metadata_plus fmp ON f.file_id = fmp.file_id
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND oc.collection_id = %s
"""
FIND_FILES_FOR_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT DISTINCT f.file_id
            FROM files f
            JOIN files_metadata fm ON f.file_id = fm.file_id
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND oc.collection_id = %s
"""
INSERT_FILE = """
            INSERT INTO 
            files (file_name, file_path, collection_id)
            VALUES (%s, %s, %s)
"""
DELETE_FILES_BY_FILE_ID = """
            DELETE 
            FROM files
            WHERE file_id in %s
            """
# COLLECTION RELATED QUERIES
FIND_COLLECTIONS_BY_ORGANIZATION_ID = """
            SELECT c.collection_id, c.collection_name, c.description
            FROM collections c 
            JOIN organization_collections oc ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s
            """
FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT *
            FROM collections c 
            JOIN organization_collections oc ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s 
            AND c.collection_id = %s
            """
FIND_COLLECTIONS_BY_COLLECTION_NAME = """
            SELECT *
            FROM collections
            WHERE collection_name = %s
            """
FIND_COLLECTIONS_BY_COLLECTION_ID = """
            SELECT *
            FROM collections
            WHERE collection_id = %s
            """
DELETE_COLLECTION_BY_COLLECTION_ID = """
            DELETE 
            FROM collections
            WHERE collection_id = %s
            """
FIND_FILES_COLLECTION_BY_FILE_IDS = """
            SELECT f.file_id, f.collection_id
            FROM files_collections f
            WHERE f.file_id IN %s
            """
INSERT_COLLECTION = """
            INSERT INTO 
            collections (collection_name, description, metatadata_prompt_prelude) 
            VALUES (%s, %s, %s)
            """
FIND_CUSTOM_INSTRUCTIONS_BY_COLLECTION_ID = """
            SELECT custom_instructions
            FROM collections
            WHERE collection_id = %s
            """
UPDATE_COLLECTION = """
            UPDATE collections 
            SET collection_name = %s, 
            description = %s
            WHERE collection_id = %s
            """
UPDATE_CUSTOM_INSTRUCTION_IN_COLLECTION = """
            UPDATE collections 
            SET custom_instructions = %s
            WHERE collection_id = %s
            """
UPDATE_METADATA_PROMPT_IN_COLLECTION_BY_COLLECTION_ID = """
            UPDATE collections 
            SET metatadata_prompt = %s 
            WHERE collection_id = %s
            """
UPDATE_COLLECTION_RULE_IN_COLLECTION_BY_COLLECTION_ID = """
            UPDATE collections
            SET collection_rule = %s
            WHERE collection_id = %s
            """

# FILES COLLECTION RELATED QUERIES
DELETE_FILES_COLLECTION_BY_COLLECTION_ID = """
            DELETE 
            FROM files_collections
            WHERE collection_id = %s
            """
UPDATE_COLLECTION_ID_IN_FILES_COLLECTION_BY_FILE_IDS_AND_ORGANIZATION_ID = """
            UPDATE files_collections fc
            INNER JOIN files f ON fc.file_id = f.file_id
            INNER JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            SET fc.collection_id = %s
            WHERE f.file_id IN %s AND oc.org_id = %s
            """
INSERT_MANY_FILES_COLLECTION = """
            INSERT INTO files_collections (file_id, collection_id)
            VALUES (%s, %s)
            """
DELETE_FROM_FILES_COLLECTION_BY_FILE_ID = """
            DELETE 
            FROM files_collections
            WHERE file_id in %s
            """

# FILES METADATA PLUS RELATED QUERIES
UPDATE_METADATA_IN_FILES_METADATA_PLUS_BY_FILE_ID = """
            UPDATE files_metadata_plus
            SET metadata = %s
            WHERE file_id = %s
            """
INSERT_FILES_METADATA_PLUS = """
            INSERT INTO files_metadata_plus (file_id, metadata)
            VALUES (%s, %s)
            """
FIND_FILES_METADATA_PLUS_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT f.file_name, fmp.metadata
            FROM files_metadata_plus fmp
            JOIN files f ON fmp.file_id = f.file_id
            JOIN files_collections fc ON fc.file_id = f.file_id
            JOIN collections c ON fc.collection_id = c.collection_id
            JOIN organization_collections oc ON oc.collection_id = fc.collection_id
            JOIN organization o ON o.org_id = oc.org_id
            WHERE o.org_id = %s AND c.collection_id = %s
            """

# FILE METADATA RELATED QUERIES
UPDATE_METADATA_IN_FILES_METADATA_BY_FILE_ID = """
            UPDATE files_metadata
            SET title = %s, summary_short = %s, summary_long = %s
            WHERE file_id = %s
            """
FIND_FILES_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT fm.file_name, fm.title, fm.summary_short, fm.summary_long
            FROM files_metadata fm
            JOIN files f ON fm.file_id = f.file_id
            JOIN files_collections fc ON fc.file_id = f.file_id
            JOIN collections c ON fc.collection_id = c.collection_id
            JOIN organization_collections oc ON oc.collection_id = fc.collection_id
            JOIN organization o ON o.org_id = oc.org_id
            WHERE o.org_id = %s AND c.collection_id = %s
            """
INSERT_FILES_METADATA = """
            INSERT INTO files_metadata (file_id, file_name, title, summary_short, summary_long)
            VALUES (%s, %s, %s, %s, %s)
            """

# ORGANIZATION COLLECTION RELATED QUERIES
DELETE_ORGANIZATION_COLLECTION_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            DELETE 
            FROM organization_collections
            WHERE org_id = %s 
            AND collection_id = %s
            """
INSERT_ORGANIZATION_COLLECTION = """
            INSERT INTO 
            organization_collections (org_id, collection_id) 
            VALUES (%s, %s)
            """

# DOCGUIDE FILES RELATED QUERIES
FIND_DOCGUIDE_FILES_BY_FILE_IDS = """
            SELECT *
            FROM docguide_files
            WHERE file_id = %s
            """
FIND_DOCGUIDE_FILES_BY_ORGANIZATION_ID = """
            SELECT df.*, f.collection_id
            FROM docguide_files df
            JOIN files f ON df.doc_file_id = f.file_id
            WHERE df.org_id = %s
            """
INSERT_DOCGUIDE_FILES = """
            INSERT INTO 
            docguide_files (file_name, org_id, doc_file_id) 
            VALUES (%s, %s, %s)
            """
DELETE_DOCGUIDE_FILES_BY_FILE_IDS_AND_ORGANIZATION_ID = """
            DELETE 
            FROM docguide_files
            WHERE file_id in %s
            AND org_id = %s
            """

# PROMPT RELATED QUERIES
FIND_PROMPT_BY_PROMPT_TYPE = """
            SELECT 
            prompt_name, prompt_text, name_label, description 
            FROM prompts 
            WHERE prompt_type = %s
            """
FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME = """
            SELECT 
            prompt_name, prompt_text, name_label, description 
            FROM prompts 
            WHERE prompt_type = %s and prompt_name = %s
            """

# DOCGUIDE SECTIONS RELATED QUERIES
FIND_DOCGUIDE_SECTIONS_BY_ORGANIZATION_ID_AND_FILE_ID = """
            SELECT *
            FROM docguide_sections f
            WHERE org_id = %s and file_id = %s
            """
FIND_DOCGUIDE_SECTIONS_BY_SECTION_ID = """
            SELECT *
            FROM docguide_sections f
            WHERE section_id = %s
            """
FIND_DOCGUIDE_SECTION_BY_ORGANIZATION_ID_AND_FILE_ID_AND_SECTION_ID = """
            SELECT *
            FROM docguide_sections f
            WHERE org_id = %s and file_id = %s and section_id = %s
            """
FIND_DOCGUIDE_SECTION_BY_ORGANIZATION_ID_AND_FILE_ID_AND_ORDER_NUMBER = """
            SELECT *
            FROM docguide_sections f
            WHERE org_id = %s AND file_id = %s AND order_number = %s
            """
DELETE_DOCGUIDE_SECTIONS_BY_FILE_IDS_AND_ORGANIZATION_ID = """
            DELETE
            FROM docguide_sections
            WHERE file_id in %s
            AND org_id = %s
            """

# DOCGUIDE FAQ RELATED QUERIES
FIND_DOCGUIDE_FAQ_BY_FILE_ID_AND_ORGANIZATION_ID = """
            SELECT * 
            FROM docguide_faq
            WHERE file_id = %s
            AND org_id = %s
            """
DELETE_DOCGUIDE_FAQ_BY_FILE_IDS_AND_ORGANIZATION_ID = """
            DELETE
            FROM docguide_faq
            WHERE file_id in %s
            AND org_id = %s
            """

# DOCGUIDE SECTIONS LEARNED STATUS RELATED QUERIES
INSERT_DOCGUIDE_SECTIONS_LEARNED_STATUS = """
            INSERT INTO
            docguide_sections_learned_status (org_id, section_id, user_id, learned_status)
            VALUES (%s, %s, %s, %s)
            """
REPLACE_DOCGUIDE_SECTIONS_LEARNED_STATUS = """
            REPLACE INTO
            docguide_sections_learned_status (org_id, section_id, user_id, learned_status)
            VALUES (%s, %s, %s, %s)
            """
UPDATE_STATUS_OF_DOCGUIDE_SECTIONS_LEARNED_STATUS = """
            UPDATE
            docguide_sections_learned_status 
            SET learned_status = %s, assessment_score = %s
            WHERE org_id = %s AND user_id = %s AND section_id = %s
            """
FIND_DOCGUIDE_SECTIONS_LEARNED_STATUS_BY_ORGANIZATION_ID_AND_USER_ID_AND_SECTION_IDS = """
            SELECT * 
            FROM docguide_sections_learned_status
            WHERE org_id = %s AND user_id = %s AND section_id in %s
            """

# DOCCHAT FAQ RELATED QUERIES
INSERT_DOCCHAT_FAQ = """
            INSERT INTO 
            docchat_faq (faq_question, faq_answer, collection_id, org_id)
            VALUES (%s, %s, %s, %s)
            """
UPDATE_DOCCHAT_FAQ_QUESTION = """
            UPDATE
            docchat_faq
            SET faq_question = %s
            WHERE faq_id = %s
            """
UPDATE_DOCCHAT_FAQ_ANSWER = """
            UPDATE
            docchat_faq
            SET faq_answer = %s
            WHERE faq_id = %s
            """
DELETE_DOCCHAT_FAQ = """
            DELETE FROM 
            docchat_faq
            WHERE faq_id in %s
            """
FIND_DOCCHAT_FAQ_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT * 
            FROM docchat_faq
            WHERE org_id = %s AND collection_id = %s
            """
FIND_DOCCHAT_FAQ_BY_FAQ_IDS = """
            SELECT * 
            FROM docchat_faq
            WHERE faq_id in %s
            """

# DOCCHAT METADATA RELATED QUERIES
INSERT_DOCCHAT_METADATA = """
            INSERT INTO
            docchat_metadata (org_id, collection_id, file_id, schema_id, field, value, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
REPLACE_DOCCHAT_METADATA = """
            REPLACE INTO
            docchat_metadata (org_id, collection_id, schema_id, file_id, field, value)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
FIND_DOCCHAT_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT * 
            FROM docchat_metadata
            WHERE org_id = %s AND collection_id = %s
            """
FIND_DOCCHAT_METADATA_WITH_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT * 
            FROM docchat_metadata dm
            INNER JOIN docchat_metadata_schema dms ON dms.schema_id = dm.schema_id
            WHERE dm.org_id = %s AND dm.collection_id = %s
            """
DELETE_DOCCHAT_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID_AND_SCHEMA_IDS = """
            DELETE 
            FROM docchat_metadata
            WHERE org_id = %s AND collection_id = %s AND schema_id in %s
            """
UPDATE_VALUE_IN_DOCCHAT_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID_FILE_ID_AND_FIELD = """
            UPDATE docchat_metadata
            SET value = %s
            WHERE org_id = %s AND collection_id = %s AND file_id = %s AND field = %s
            """

# DOCCHAT METADATA SCHEMA RELATED QUERIES
INSERT_DOCCHAT_METADATA_SCHEMA = """
            INSERT INTO
            docchat_metadata_schema (org_id, collection_id, field, description, order_number)
            VALUES (%s, %s, %s, %s, %s)
            """
FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT * 
            FROM docchat_metadata_schema
            WHERE org_id = %s AND collection_id = %s
            """
FIND_DOCCHAT_METADATA_SCHEMA_BY_SCHEMA_IDS = """
            SELECT * 
            FROM docchat_metadata_schema
            WHERE schema_id in %s
            """
UPDATE_FIELD_AND_DESCRIPTION_IN_DOCCHAT_METADATA_BY_SCHEMA_ID = """
            UPDATE docchat_metadata_schema
            SET field = %s, description = %s
            WHERE schema_id = %s
"""
UPDATE_ORDER_NUMBER_IN_DOCCHAT_METADATA_BY_SCHEMA_ID = """
            UPDATE docchat_metadata_schema
            SET order_number = %s
            WHERE schema_id = %s
"""
DELETE_DOCCHAT_METADATA_BY_SCHEMA_ID = """
            DELETE FROM docchat_metadata_schema
            WHERE schema_id = %s
"""



##########################################################
####################### V2 ###############################
##########################################################

V2_INSERT_FILE = """
            INSERT INTO 
            files (file_name, file_path, collection_id)
            VALUES (%s, %s, %s)
"""

FIND_MODULES_BY_MODULE_ID = """
            SELECT *
            FROM modules
            WHERE id = %s
"""

FIND_FILES_FROM_FILES_COLLECTIONS_BY_FILE_IDS = """
            SELECT * 
            FROM files_collections
            WHERE file_id in %s
"""


V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID = """
            SELECT *
            FROM collections c 
            WHERE org_id = %s AND module_id IS NOT NULL
            """

V2_FIND_FILES_BY_COLLECTION_IDS = """
            SELECT *
            FROM files f
            Where collection_id in %s
"""

V2_UPDATE_COLLECTION_ID_IN_FILES_BY_FILE_IDS = """
            UPDATE files
            SET collection_id = %s
            WHERE file_id in %s
"""

V2_INSERT_INTO_COLLECTIONS = """
            INSERT INTO
            collections (collection_name, description, metatadata_prompt_prelude, org_id, module_id)
            VALUES (%s, %s, %s, %s, %s)
"""

V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT *
            FROM collections c
            WHERE c.org_id = %s 
            AND c.collection_id = %s
            """
