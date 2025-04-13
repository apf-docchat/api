SET AUTOCOMMIT=0; -- Disable auto-commit
SET SESSION sql_mode = 'STRICT_ALL_TABLES';

-- Begin a transaction
START TRANSACTION;

-- Update `docguide_sections_learned_status` table: Modify `learned_status` and `assessment_score`, add a unique key
ALTER TABLE `docguide_sections_learned_status`
    MODIFY COLUMN `learned_status` ENUM('INITIAL', 'PARTIAL', 'FULL') COLLATE latin1_bin NOT NULL,
    ADD UNIQUE KEY `org_id` (`org_id`, `user_id`, `section_id`) USING BTREE;

-- Update `files_collections` table: Remove default values from `file_id` and `collection_id`
ALTER TABLE `files_collections`
    MODIFY COLUMN `file_id` INT NOT NULL,
    MODIFY COLUMN `collection_id` INT NOT NULL;

-- Update `log_ai_calls` table: Adjust the `username` key definition
ALTER TABLE `log_ai_calls`
DROP KEY `username`,
  ADD KEY `username` (`username`);

-- Update `organization` table: Change default value of `updated_date`
ALTER TABLE `organization`
    MODIFY COLUMN `updated_date` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Update `organization_collections` table: Remove default values from `org_id` and `collection_id`
ALTER TABLE `organization_collections`
    MODIFY COLUMN `org_id` INT NOT NULL,
    MODIFY COLUMN `collection_id` INT NOT NULL;

-- Update `organization_modules` table: Remove foreign key constraints
ALTER TABLE `organization_modules`
DROP FOREIGN KEY `organization_modules_ibfk_1`,
  DROP FOREIGN KEY `organization_modules_ibfk_2`;

-- Commit the transaction
COMMIT;
