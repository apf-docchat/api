# USER RELATED QUERIES
FIND_USER_BY_USERNAME = "SELECT id, password_hash FROM users WHERE username = %s"
FIND_USERID_BY_USERNAME = "SELECT id FROM users WHERE username = %s and is_active = 1"
FIND_USER_BY_EMAIL = "SELECT * FROM users WHERE email = %s"
FIND_USER_BY_USER_ID = "SELECT * FROM users WHERE id = %s"
FIND_SUPERUSER_BY_ORG_ID = "SELECT user_id FROM user_organization WHERE org_id = %s AND role = 'SUPER_USER'"
FIND_ALL_USERNAMES = "SELECT id, username, email FROM users where is_active = 1"

FIND_USER_BY_PHONE_NUMBER = """
            SELECT * 
            FROM users
            WHERE phone_number = %s
            """
V2_FIND_USER_ADMIN_BY_USER_ID = """
              SELECT is_admin FROM users WHERE id = %s
              """

INSERT_USER = """
            INSERT INTO `users` (`username`, `password_hash`, `email`) VALUES (%s, %s, %s)
            """
INSERT_USER_2 = """
            INSERT INTO `users` (`username`, `first_name`, `last_name`, `password_hash`, `email`) VALUES (%s, %s, %s, %s, %s)
            """

UPDATE_USER_NAME = """
            UPDATE users
            SET username = %s
            WHERE id = %s
            """

UPDATE_EMAIL = """
            UPDATE users
            SET email = %s
            WHERE id = %s
            """


# ORGANIZATION RELATED QUERIES
FIND_ORGANIZATION_BY_USER_ID = """
            SELECT o.org_id, o.org_name, uo.role
            FROM organization o
            JOIN user_organization uo ON o.org_id = uo.org_id
            JOIN users u ON u.id = uo.user_id
            WHERE u.id = %s
            """
FIND_ORGANIZATION_BY_USER_ID_SUPER_USER = """
            SELECT o.org_id, o.org_name, uo.role
            FROM organization o
            JOIN user_organization uo ON o.org_id = uo.org_id
            JOIN users u ON u.id = uo.user_id
            WHERE u.id = %s and uo.role = 'SUPER_USER'
            """
FIND_ORGANIZATION_BY_USER_ID_AND_ORG_ID_SUPER_USER = """
            SELECT o.org_id, o.org_name, uo.role
            FROM organization o
            JOIN user_organization uo ON o.org_id = uo.org_id
            JOIN users u ON u.id = uo.user_id
            WHERE u.id = %s and uo.role = 'SUPER_USER' and o.org_id = %s
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
FIND_ORG_NAME_BY_ORG_ID = """
            SELECT org_name
            FROM organization
            WHERE org_id = %s
            """
FIND_ORG_ID_BY_USER_ID = """
            SELECT org_id
            FROM user_organization
            WHERE user_id = %s
            """
FIND_CLIENT_ID_BY_ORG_ID = """
            SELECT clientid
            FROM organization
            WHERE org_id = %s
            """
V2_INSERT_USER_ORGANIZATION = """
              INSERT INTO
              user_organization (user_id, org_id, role)
              VALUES (%s, %s, %s)
              """

V2_FIND_ORGANIZATION_MODULE = """
              SELECT * FROM organization_modules WHERE org_id = %s AND module_id = %s
              """

V2_DELETE_ORGANIZATION_MODULES_BY_ORG_ID = """
              DELETE FROM organization_modules WHERE org_id = %s
              """

V2_UPDATE_ORG_NAME = """
              UPDATE organization SET org_name = %s WHERE org_id = %s
              """
V2_INSERT_ORGANIZATION = """
            INSERT INTO
            organization (org_name, status, clientid)
            VALUES (%s, 'ACTIVE', %s)
            """

V2_INSERT_ORGANIZATION_MODULES = """
              INSERT INTO 
              organization_modules (org_id, module_id)
              VALUES (%s, %s)
              """

V2_FIND_ORGANIZATION_BY_ORG_NAME = """
              SELECT * FROM organization WHERE org_name = %s
              """
FIND_ORGANIZATION_BY_COLLECTION_ID = """
            SELECT o.org_id, o.org_name
            FROM organization o
            JOIN collections c ON c.org_id = o.org_id
            WHERE c.collection_id = %s
            """
FIND_ORG_BY_CLIENTID = """
            SELECT o.org_id, o.org_name
            FROM organization o
            WHERE clientid = %s
            """

#POPUPBOT RELATED QUERIES
FIND_ORG_BY_URL_SLUG = """
            SELECT o.org_id, o.org_name
            FROM organization o
            JOIN organization_popupbot op ON o.org_id = op.org_id
            WHERE op.url_slug = %s
            """
FIND_URLSLUG_BY_ORG_ID = """
            SELECT url_slug
            FROM organization_popupbot
            WHERE org_id = %s
            """
FIND_CHATMODE_BY_ORG_ID = """
            SELECT chat_mode
            FROM organization_popupbot
            WHERE org_id = %s
            """
INSERT_ORG_POPUPBOT_CONFIG = """
            INSERT INTO organization_popupbot (org_id, allowed_domains, url_slug, chat_mode)
            VALUES (%s, %s, %s, %s)
            """
UPDATE_URL_SLUG_BY_ORG_ID = """
            UPDATE organization_popupbot
            SET url_slug = %s
            WHERE org_id = %s
            """

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
FIND_MODULES_BY_MODULE_ID = """
            SELECT *
            FROM modules
            WHERE id = %s
            """

# FILES RELATED QUERIES
""" FIND_FILES_BY_ORGANIZATION_ID = "
            SELECT f.file_id, f.file_name, c.collection_name, c.collection_id  
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN collections c ON fc.collection_id = c.collection_id
            JOIN organization_collections oc ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s
            """
""" FIND_FILES_BY_COLLECTION_IDS = "
            SELECT f.file_id, f.file_name, fc.collection_id, f.upload_datetime
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            WHERE fc.collection_id IN %s
            ORDER BY f.upload_datetime DESC
            """
""" FIND_FILES_WITH_DOCGUIDE_FILES_BY_COLLECTION_IDS = "
            SELECT f.file_id, f.file_name, fc.collection_id
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN docguide_files df ON f.file_id = df.doc_file_id
            WHERE fc.collection_id IN %s
            """
FIND_FILES_BY_FILES_IDS = """
            SELECT *
            FROM files f
            WHERE f.file_id IN %s
            """
FIND_FILE_BY_FILES_ID = """
            SELECT *
            FROM files f
            WHERE f.file_id = %s
            """
""" FIND_FILES_COUNT_BY_COLLECTION_ID_AND_ORGANIZATION_ID = "
            SELECT COUNT(*) AS total
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            JOIN collections c ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND c.collection_id = %s
            """
""" FIND_FILES_COUNT_OF_METADATA_BY_COLLECTION_ID_AND_ORGANIZATION_ID = "
            SELECT COUNT(*) AS total
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            JOIN collections c ON c.collection_id = oc.collection_id
            JOIN files_metadata fm ON fm.file_id = f.file_id
            WHERE oc.org_id = %s AND c.collection_id = %s
            """
""" FIND_FILES_COUNT_OF_METADATA_PLUS_BY_COLLECTION_ID_AND_ORGANIZATION_ID = "
            SELECT COUNT(*) AS total
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            JOIN collections c ON c.collection_id = oc.collection_id
            JOIN files_metadata_plus fmp ON fmp.file_id = f.file_id
            WHERE oc.org_id = %s AND c.collection_id = %s
            """
""" FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID = "
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
            files (file_name, file_path)
            VALUES (%s, %s)
"""
INSERT_FILE_METADATA = """
            INSERT INTO
            files_metadata (file_id, file_name, file_description, training, handout, media)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
DELETE_FILES_BY_FILE_ID = """
            DELETE 
            FROM files
            WHERE file_id in %s
            """
DELETE_FILES_METADATA_BY_FILE_ID = """
            DELETE 
            FROM files_metadata
            WHERE file_id in %s
            """
DELETE_FILES_METADATA_PLUS_BY_FILE_ID = """
            DELETE 
            FROM files_metadata_plus
            WHERE file_id in %s
            """
V2_FIND_FILES_COUNT_OF_METADATA_BY_COLLECTION_ID_AND_ORGANIZATION_ID = """
            SELECT COUNT(*) AS total
            FROM files f
            JOIN collections c ON c.collection_id = f.collection_id
            JOIN files_metadata fm ON fm.file_id = f.file_id
            WHERE c.org_id = %s AND c.collection_id = %s
            """

V2_FIND_FILES_COUNT_OF_METADATA_PLUS_BY_COLLECTION_ID_AND_ORGANIZATION_ID = """
            SELECT COUNT(*) AS total
            FROM files f
            JOIN collections c ON c.collection_id = f.collection_id
            JOIN files_metadata_plus fmp ON fmp.file_id = f.file_id
            WHERE c.org_id = %s AND c.collection_id = %s
            """
V2_FIND_FILES_FOR_METADATA_PLUS_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT DISTINCT f.file_id
            FROM files f
            JOIN collections c ON f.collection_id = c.collection_id
            JOIN files_metadata_plus fmp ON f.file_id = fmp.file_id
            WHERE c.org_id = %s AND f.collection_id = %s
"""

V2_FIND_FILES_FOR_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT DISTINCT f.file_id
            FROM files f
            JOIN collections c ON f.collection_id = c.collection_id
            JOIN files_metadata fm ON f.file_id = fm.file_id
            WHERE c.org_id = %s AND f.collection_id = %s
"""
V2_FIND_FILE_DETAILS_BY_COLLECTION_ID = """
            SELECT f.file_id, fm.file_name, fm.file_description, fm.handout, f.file_url, fm.media
            FROM files f
            JOIN collections c ON f.collection_id = c.collection_id
            JOIN files_metadata fm ON f.file_id = fm.file_id
            WHERE f.collection_id = %s
"""
FIND_GSHEETS_BY_COLLECTION_ID = """
            SELECT f.file_id, f.file_name, f.file_url
            FROM files f
            JOIN collections c ON f.collection_id = c.collection_id
            WHERE c.collection_id = %s AND c.type = 'googlesheet' and f.file_url IS NOT NULL
            """

V2_INSERT_FILE = """
            INSERT INTO 
            files (file_name, file_path, collection_id, file_url)
            VALUES (%s, %s, %s, %s)
"""

V2_FIND_FILES_METADATA_PLUS_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT f.file_name, fmp.metadata
            FROM files_metadata_plus fmp
            JOIN files f ON fmp.file_id = f.file_id
            JOIN collections c ON f.collection_id = c.collection_id
            JOIN organization o ON o.org_id = c.org_id
            WHERE o.org_id = %s AND c.collection_id = %s
            """

V2_FIND_FILES_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT fm.file_name, fm.title, fm.summary_short, fm.summary_long
            FROM files_metadata fm
            JOIN files f ON fm.file_id = f.file_id
            JOIN collections c ON f.collection_id = c.collection_id
            JOIN organization o ON o.org_id = c.org_id
            WHERE o.org_id = %s AND c.collection_id = %s
            """
V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT *
            FROM files f
            JOIN collections c ON f.collection_id = c.collection_id
            WHERE c.collection_id = %s AND c.org_id = %s
            """
FIND_FILES_METADATA_BY_FILE_ID = """
            SELECT *
            FROM files_metadata
            WHERE file_id = %s
            """
# COLLECTION RELATED QUERIES
""" FIND_COLLECTIONS_BY_ORGANIZATION_ID = "
            SELECT c.collection_id, c.collection_name, c.description
            FROM collections c 
            JOIN organization_collections oc ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s
            """
""" FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID = "
            SELECT *
            FROM collections c 
            JOIN organization_collections oc ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s 
            AND c.collection_id = %s
            """
FIND_COLLECTIONS_BY_COLLECTION_NAME = """
            SELECT c.*, JSON_UNQUOTE(JSON_EXTRACT(cc.credentials_json, '$.db_uri')) as db_uri
            FROM collections c
            LEFT JOIN collections_credentials cc ON c.credential_id = cc.id
            WHERE c.collection_name = %s
            """

""" old one
            SELECT *
            FROM collections
            WHERE collection_name = %s
            """

FIND_COLLECTIONS_BY_COLLECTION_ID = """
            SELECT c.*, JSON_UNQUOTE(JSON_EXTRACT(cc.credentials_json, '$.db_uri')) as db_uri
            FROM collections c
            LEFT JOIN collections_credentials cc ON c.credential_id = cc.id
            WHERE c.collection_id = %s
            """

""" old one
            SELECT *
            FROM collections
            WHERE collection_id = %s
            """
FIND_COLLECTIONS_BY_NAME_AND_ORG_ID = """
            SELECT c.*, JSON_UNQUOTE(JSON_EXTRACT(cc.credentials_json, '$.db_uri')) as db_uri
            FROM collections c
            LEFT JOIN collections_credentials cc ON c.credential_id = cc.id
            WHERE c.collection_name = %s AND c.org_id = %s
            """

""" old one
            SELECT *
            FROM collections
            WHERE collection_name = %s AND org_id = %s
            """
FIND_GOOGLE_CREDENTIALS_BY_COLLECTION_ID = """
            SELECT cc.credentials_json
            FROM collections_credentials cc
            JOIN collections c ON cc.id = c.credential_id
            WHERE c.collection_id = %s
            """
DELETE_COLLECTION_BY_COLLECTION_ID = """
            DELETE 
            FROM collections
            WHERE collection_id = %s
            """
""" FIND_FILES_COLLECTION_BY_FILE_IDS = "
            SELECT f.file_id, f.collection_id
            FROM files_collections f
            WHERE f.file_id IN %s
            """
""" INSERT_COLLECTION = "
            INSERT INTO 
            collections (collection_name, description, metatadata_prompt_prelude) 
            VALUES (%s, %s, %s)
            """
FIND_CUSTOM_INSTRUCTIONS_BY_COLLECTION_ID = """
            SELECT custom_instructions
            FROM collections
            WHERE collection_id = %s
            """
""" UPDATE_COLLECTION = "
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
FIND_FILES_FROM_FILES_COLLECTIONS_BY_FILE_IDS = """
            SELECT * 
            FROM files_collections
            WHERE file_id in %s
"""
FIND_COLLECTION_INSIGHTS_LIST_BY_COLLECTION_ID = """
            SELECT id, order_number, title, file_path_uuid, query, updated_at
            FROM collections_insights
            WHERE collection_id = %s and is_active = 1
            ORDER BY order_number
            """

FIND_COLLECTION_INSIGHT_BY_COLLECTION_ID = """
            SELECT *
            FROM collections_insights
            WHERE collection_id = %s and id = %s
            """
FIND_COLLECTION_INSIGHTS_BY_COLLECTION_ID = """
            SELECT *
            FROM collections_insights
            WHERE collection_id = %s
            """

FIND_COLLECTIONS_WITHOUT_INSIGHTS_FOR_ORG_WITHIN_TIMEFRAME = """
            SELECT c.collection_id, c.collection_name, c.description
            FROM collections c
            WHERE c.collection_id NOT IN (SELECT collection_id FROM collections_insights) AND c.org_id = %s AND c.created_at >= %s
            AND c.created_at <= %s
"""

INSERT_COLLECTION_INSIGHT = """
            INSERT INTO
            collections_insights (collection_id, query, title, order_number, creator_user_id, file_path_uuid)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
UPDATE_COLLECTION_INSIGHT = """
            UPDATE collections_insights
            SET query = %s, title = %s, updated_at = NOW(), updater_user_id = %s
            WHERE id = %s
            """
DELETE_COLLECTION_INSIGHT = """
            UPDATE collections_insights
            SET is_active = 0, updated_at = NOW(), updater_user_id = %s
            WHERE id = %s
            """
V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID = """
            SELECT c.*, JSON_UNQUOTE(JSON_EXTRACT(cc.credentials_json, '$.db_uri')) as db_uri
            FROM collections c
            LEFT JOIN collections_credentials cc ON c.credential_id = cc.id
            WHERE c.org_id = %s AND c.module_id IS NOT NULL
            AND c.collection_id IN %s
            """

""" old one
            SELECT *
            FROM collections c 
            WHERE c.org_id = %s AND c.module_id IS NOT NULL
            AND c.collection_id IN %s
            """
V2_FIND_ALL_COLLECTIONS_BY_ORGANIZATION_ID = """
            SELECT c.*, JSON_UNQUOTE(JSON_EXTRACT(cc.credentials_json, '$.db_uri')) as db_uri
            FROM collections c
            LEFT JOIN collections_credentials cc ON c.credential_id = cc.id
            WHERE c.org_id = %s AND c.module_id IS NOT NULL
            """

""" old one
            SELECT *
            FROM collections c 
            WHERE c.org_id = %s AND c.module_id IS NOT NULL
            """
V2_UPDATE_COLLECTION_ID_IN_FILES_BY_FILE_IDS = """
            UPDATE files
            SET collection_id = %s
            WHERE file_id in %s
"""

V2_INSERT_INTO_COLLECTIONS = """
            INSERT INTO
            collections (collection_name, description, metatadata_prompt_prelude, org_id, module_id, user_id, sharing_level, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
V2_FIND_GOOGLESHEET_COLLECTIONS_CREDENTIALS_ID = """
            SELECT id
            FROM collections_credentials
            WHERE service_type = %s
            """
V2_FIND_GOOGLESHEET_COLLECTIONS_CREDENTIALS_JSON = """
            SELECT credentials_json
            FROM collections_credentials
            WHERE service_type = %s
            """
V2_INSERT_INTO_COLLECTIONS_CREDENTIALS_DB_URI = """
            INSERT INTO collections_credentials (service_type, credentials_json)
            VALUES (%s, %s)
            """
V2_UPDATE_COLLECTIONS_WITH_CREDENTIAL_ID = """
            UPDATE collections
            SET credential_id = %s
            WHERE collection_id = %s
            """
V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID = """
            SELECT c.*, JSON_UNQUOTE(JSON_EXTRACT(cc.credentials_json, '$.db_uri')) as db_uri
            FROM collections c
            LEFT JOIN collections_credentials cc ON c.credential_id = cc.id
            WHERE c.org_id = %s AND c.module_id IS NOT NULL
            AND c.collection_id = %s
            """

""" old one
            SELECT *
            FROM collections c
            WHERE c.org_id = %s AND c.module_id IS NOT NULL
            AND c.collection_id = %s
            """

V2_FIND_FILES_BY_COLLECTION_IDS = """
            SELECT *
            FROM files f
            WHERE collection_id IN %s
            ORDER BY f.upload_datetime DESC
            """

V2_FIND_FILES_BY_COLLECTION_ID = """
    SELECT 
        f.file_id,
        f.file_name,
        f.file_path,
        f.upload_datetime,
        f.collection_id,
        fm.title,
        fm.summary_short
    FROM 
        files f
    LEFT JOIN 
        files_metadata fm ON f.file_id = fm.file_id
    WHERE 
        f.collection_id = %s
    ORDER BY 
        f.upload_datetime DESC
"""

V2_FIND_FILES_BY_FILE_IDS = """
    SELECT 
        f.file_id,
        f.file_name,
        f.file_path,
        f.upload_datetime,
        f.collection_id,
        fm.title,
        fm.summary_short
    FROM 
        files f
    LEFT JOIN 
        files_metadata fm ON f.file_id = fm.file_id
    WHERE 
        f.file_id IN %s
"""

V2_FIND_FILES_COUNT_BY_COLLECTION_ID_AND_ORGANIZATION_ID = """
            SELECT COUNT(*) AS total
            FROM files f
            JOIN collections c ON c.collection_id = f.collection_id
            WHERE c.org_id = %s AND f.collection_id = %s
            """
FIND_FAQ_IDS_BY_QUERY = """
            SELECT faq_id, query, script
            FROM collections_faq
            WHERE collection_id = %s
            """
INSERT_COLLECTION_FAQ = """
            INSERT INTO collections_faq (collection_id, query, script, user_id)
            VALUES (%s, %s, %s, %s)
            """
UPDATE_COLLECTIONS_FAQ = """
            UPDATE collections_faq
            SET script = %s, updated_at = NOW(), user_id = %s
            WHERE faq_id = %s
            """
DELETE_COLLECTIONS_FAQ = """
            DELETE FROM collections_faq
            WHERE faq_id = %s
            """
# FILES COLLECTION RELATED QUERIES
DELETE_FILES_COLLECTION_BY_COLLECTION_ID = """
            DELETE 
            FROM files_collections
            WHERE collection_id = %s
            """
""" UPDATE_COLLECTION_ID_IN_FILES_COLLECTION_BY_FILE_IDS_AND_ORGANIZATION_ID = "
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
UPDATE_METADATA_IN_FILES_METADATA_BY_FILE_ID_2 = """
            UPDATE files_metadata
            SET training = %s, handout = %s, file_description = %s
            WHERE file_id = %s
            """
""" FIND_FILES_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID = "
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
# This set of queries is not used in v2
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
V2_FIND_ALL_PROMPTS = """
              SELECT * FROM prompts
              """

V2_FIND_PROMPT_BY_ID = """
    SELECT * FROM prompts WHERE id = %s
"""

V2_INSERT_PROMPT_ARCHIVE = """
    INSERT INTO prompts_archive (prompt_id, prompt_name, name_label, prompt_text, description, prompt_type, datetime_created)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

V2_UPDATE_PROMPT = """
              UPDATE prompts SET prompt_type = %s, prompt_name = %s, name_label = %s, prompt_text = %s, description = %s WHERE id = %s
              """
V2_INSERT_PROMPT = """
              INSERT INTO prompts (prompt_type, prompt_name, name_label, prompt_text, description) VALUES (%s, %s, %s, %s, %s)
              """

V2_FIND_ARCHIVED_PROMPTS_BY_PROMPT_ID = """
              SELECT * FROM prompts_archive WHERE prompt_id = %s
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

# DOCGUIDE SESSION RELATED QUERIES
INSERT_DOCGUIDE_SESSION = """
            INSERT INTO docguide_sessions (user_id, file_id, platform)
            VALUES (%s, %s, %s)
            """

UPDATE_FILE_ID_OF_DOCGUIDE_SESSION = """
            UPDATE docguide_sessions
            SET file_id = %s, platform = %s
            WHERE user_id = %s
            """
            
UPDATE_SECTION_ID_OF_DOCGUIDE_SESSION = """
            UPDATE docguide_sessions
            SET section_id = %s
            WHERE user_id = %s
            """
            
FIND_DOCGUIDE_SESSION_BY_USER_ID = """
            SELECT * 
            FROM docguide_sessions
            WHERE user_id = %s            
            """
            
UPDATE_THREAD_ID_AND_STAGE_ID_OF_DOCGUIDE_SESSION = '''
    UPDATE docguide_sessions
    SET thread_id = %s, stage_id = %s
    WHERE user_id = %s
'''

UPDATE_STAGE_ID_OF_DOCGUIDE_SESSION = '''
    UPDATE docguide_sessions
    SET stage_id = %s
    WHERE user_id = %s
'''

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

# FILES BM25 Related queries
FIND_BM25_TERMS_FOR_FILE = """
            SELECT term, idf 
            FROM files_bm25_terms 
            WHERE file_id = %s
            """

FIND_BM25_AVG_DOC_LENGTH = """
            SELECT avg_doc_len 
            FROM files_bm25_meta 
            WHERE file_id = %s
            """

FIND_BM25_TOKENS = """
            SELECT page_number, tokens 
            FROM files_pages 
            WHERE file_id = %s ORDER BY page_number
            """
DELETE_BM25_TERMS_FOR_FILE = """
            DELETE
            FROM files_bm25_terms 
            WHERE file_id IN %s
            """
DELETE_BM25_AVG_DOC_LENGTH = """
            DELETE
            FROM files_bm25_meta 
            WHERE file_id IN %s
            """
DELETE_BM25_TOKENS = """
            DELETE
            FROM files_pages 
            WHERE file_id IN %s
            """

# ENTITIES related queries
V2_FIND_ENTITIES_BY_TYPE_USERNAME = """
            SELECT * 
            FROM entities 
            WHERE type = %s
            AND JSON_EXTRACT(data, '$.username') = %s
            """
V2_FIND_ENTITIES_BY_TYPE = """
            SELECT * 
            FROM entities 
            WHERE type = %s
            """
INSERT_ENTITY = """
            INSERT INTO entities (type, data)
            VALUES (%s, %s)
            """
UPDATE_ENTITY = """
            UPDATE entities
            SET data = %s
            WHERE id = %s AND type = %s
            """
DELETE_ENTITY = """
            DELETE FROM entities
            WHERE id = %s AND type = %s
            """
GET_ENTITY_CONFIGURATION = """
            SELECT * 
            FROM entity_configurations
            WHERE type = %s
            ORDER BY updated_at DESC
            """
V2_FIND_GENERAL_COLLECTION_RULE_CONFIGURATION = """
            SELECT data
            FROM entities
            WHERE type = 'configurations'
            """

# JOBS RELATED QUERIES
FIND_JOBS_LIST_BY_ORG_ID = """
            SELECT id, order_number, title, job_collection_id, query, steps, file_path_uuid, api_endpoint
            FROM jobs
            WHERE org_id = %s and is_active = 1
            ORDER BY order_number
            """
FIND_JOBS_LIST_BY_COLLECTION_ID = """
            SELECT id, order_number, title, job_collection_id, query, steps, file_path_uuid, api_endpoint
            FROM jobs
            WHERE job_collection_id = %s and org_id = %s and is_active = 1
            ORDER BY order_number
            """

FIND_JOB_BY_ID = """
            SELECT *
            FROM jobs
            WHERE id = %s and is_active = 1
            """
FIND_JOBS_BY_ORGS_ID = """
            SELECT *
            FROM jobs
            WHERE org_id = %s and is_active = 1
            """
FIND_JOBS_LARGEST_ORDER_NUMBER = """
            SELECT MAX(order_number) AS max_order_number
            FROM jobs
            WHERE org_id = %s and is_active = 1
            """
INSERT_JOB = """
            INSERT INTO
            jobs (title, order_number, creator_username, org_id, steps, job_collection_id, query, file_path_uuid)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
UPDATE_JOB_API_ENDPOINT = """
            UPDATE jobs
            SET api_endpoint = %s
            WHERE id = %s
            """
UPDATE_JOB_STEPS = """
            UPDATE jobs
            SET steps = %s, updated_at = NOW(), updater_username = %s, api_endpoint = %s, job_collection_id = %s
            WHERE id = %s
            """
UPDATE_JOB_STEPS_QUERY = """
            UPDATE jobs
            SET steps = %s, updated_at = NOW(), updater_username = %s, query = %s, job_collection_id = %s, api_endpoint = %s
            WHERE id = %s
            """
DELETE_JOB = """
            UPDATE jobs
            SET is_active = 0, updated_at = NOW(), updater_username = %s
            WHERE id = %s
            """
FIND_JOB_BY_API_ENDPOINT = """
            SELECT *
            FROM jobs
            WHERE api_endpoint = %s and is_active = 1
            """

# ROLES RELATED QUERIES
FIND_ROLES_LIST_BY_USER_ID = """
            SELECT id, role_name, details, objectives
            FROM user_roles
            WHERE user_id = %s and is_active = 1
            """
FIND_ROLE_BY_ID = """
            SELECT *
            FROM user_roles
            WHERE id = %s and user_id = %s and is_active = 1
            """
INSERT_ROLE = """
            INSERT INTO
            user_roles (user_id, role_name, details, objectives, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """
UPDATE_ROLE = """
            UPDATE user_roles
            SET role_name = %s, details = %s, objectives = %s, updated_at = NOW()
            WHERE id = %s and user_id = %s
            """
DELETE_ROLE = """
            UPDATE user_roles
            SET is_active = 0, updated_at = NOW()
            WHERE id = %s and user_id = %s
            """
CHANGE_USER_ROLE = """
            UPDATE user_role_current
            SET user_role_id = %s, selected_at = NOW()
            WHERE user_id = %s
            """
FIND_USER_ROLE = """
            SELECT ur.id, ur.role_name, ur.details, ur.objectives
            FROM user_role_current urc
            JOIN user_roles ur ON urc.user_role_id = ur.id
            WHERE urc.user_id = %s and ur.is_active = 1
            """
INSERT_USER_ROLE = """
            INSERT INTO
            user_role_current (user_role_id, user_id, selected_at)
            VALUES (%s, %s, NOW())
            """
DELETE_USER_ROLE_BY_ID = """
            DELETE FROM user_role_current
            WHERE user_role_id = %s and user_id = %s
            """
DELETE_USER_ALL_ROLES = """
            DELETE FROM user_role_current
            WHERE user_id = %s
            """


########### DB changes - logged for later reference ###########

### 9th Jan 2025
"""
ALTER TABLE app.collections
ADD COLUMN user_id INT NULL AFTER description,
ADD CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;


ALTER TABLE app.collections
ADD COLUMN sharing_level ENUM('ORG', 'PRIVATE', 'LIMITED') NOT NULL DEFAULT 'ORG' AFTER description,
ADD COLUMN shared_with JSON AFTER sharing_level;
"""

### 12th Jan 2025
"""
ALTER TABLE app.collections ADD type ENUM('file','db','file-db') DEFAULT 'file-db';
ALTER TABLE app.collections ADD db_uri varchar(255);
"""

### 21st Jan 2025
"""
ALTER TABLE app.collections
MODIFY COLUMN custom_instructions MEDIUMTEXT;
"""

### 22nd Jan 2025
"""
ALTER TABLE jobs
ADD COLUMN job_collection_id INT, 
ADD CONSTRAINT fk_jobs_job_collection_id
FOREIGN KEY (job_collection_id) REFERENCES collections(collection_id);
"""

### 23rd Jan
"""
ALTER TABLE jobs
ADD COLUMN query VARCHAR(1000);
"""
"""
Added ORGFILES_BASE_DIR to .env to store path of temp files needed by orgs and users
Eg: /data/orgs/org3/uuid/<filename>
"""

### 24th Jan
"""
ALTER TABLE jobs
ADD COLUMN file_path_uuid VARCHAR(200);
"""

### 9th Feb
"""
ALTER TABLE app.collections
ADD COLUMN created_at TIMESTAMP DEFAULT NOW() NOT NULL,
ADD COLUMN updated_at TIMESTAMP DEFAULT NOW() NOT NULL;
"""

### 10th Feb
"""
ALTER TABLE app.collections_insights 
MODIFY COLUMN query VARCHAR(2000) DEFAULT NULL;
"""

"""
ALTER TABLE app.collections_insights
  ADD COLUMN creator_user_id INT,
  ADD COLUMN created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  ADD COLUMN updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
  ADD COLUMN updater_user_id INT,
  ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1,
  ADD COLUMN file_path_uuid VARCHAR(36);
"""

### 1st Mar
"""
ALTER TABLE jobs
ADD COLUMN api_endpoint VARCHAR(300);
"""

### 8th Mar
"""
ALTER TABLE app.organization ADD COLUMN clientid VARCHAR(255);
"""
"""
alter table app.files add column file_url text;
"""

### 9th Mar
"""
ALTER TABLE app.files_metadata
ADD COLUMN file_description text,
ADD COLUMN training boolean,
ADD COLUMN handout boolean;
"""
"""
ALTER TABLE app.files_metadata
ADD COLUMN media boolean;
"""

### 17th Mar
"""
CREATE TABLE app.organization_popupbot (
    id INT AUTO_INCREMENT PRIMARY KEY,
    org_id INT NOT NULL,
    allowed_domains TEXT,
    url_slug VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

### 19th Mar
"""
ALTER TABLE app.organization_popupbot ADD COLUMN chat_mode VARCHAR(100);
"""

### 29th Mar
"""
ALTER TABLE `app`.`collections` 
CHANGE COLUMN `type` `type` ENUM('file', 'db', 'file-db', 'googlesheet') NULL DEFAULT 'file-db' ;
"""

### 30th Mar
"""
CREATE TABLE app.collections_credentials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_type VARCHAR(50) NOT NULL, -- e.g., 'googlesheets'
    credentials_json JSON NOT NULL,     -- Using MySQL's JSON type
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
"""

"""
ALTER TABLE app.collections
ADD COLUMN credential_id INT,
ADD CONSTRAINT fk_collections_credential FOREIGN KEY (credential_id) REFERENCES collections_credentials(id);
"""

"""
ALTER TABLE app.collections
DROP COLUMN db_uri;
"""

### 6th Apr
"""
CREATE TABLE app.collections_faq (
    faq_id int NOT NULL AUTO_INCREMENT,
    collection_id int,
    query text NOT NULL,
    script text,
    created_at timestamp DEFAULT current_timestamp,
    updated_at timestamp DEFAULT current_timestamp ON UPDATE current_timestamp,
    user_id int,
    PRIMARY KEY (faq_id),
    foreign key (collection_id) references app.collections(collection_id)
);
"""