-- Change column type in docchat_faq
ALTER TABLE docchat_faq
    MODIFY COLUMN faq_question TEXT NOT NULL;

-- Change column type in docchat_metadata_schema
ALTER TABLE docchat_metadata_schema
    MODIFY COLUMN description TEXT NOT NULL;

-- Change column type in docguide_faq
ALTER TABLE docguide_faq
    MODIFY COLUMN faq_content TEXT NOT NULL;

-- Change column type in docguide_sections
ALTER TABLE docguide_sections
    MODIFY COLUMN section_content TEXT NOT NULL;

-- Add composite primary key in docchat_metadata
ALTER TABLE docchat_metadata
    ADD PRIMARY KEY (org_id, collection_id, file_id, schema_id);

-- Add composite primary key in docguide_sections_learned_status
ALTER TABLE docguide_sections_learned_status
    ADD PRIMARY KEY (org_id, user_id, section_id);

-- Change column default in users
ALTER TABLE users
    MODIFY COLUMN last_login TIMESTAMP;
