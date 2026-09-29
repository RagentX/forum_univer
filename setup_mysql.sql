-- Выполнить один раз в MySQL Workbench под root.
CREATE DATABASE IF NOT EXISTS forum_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS forum_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'forum'@'%' IDENTIFIED BY 'forumpass';
GRANT ALL PRIVILEGES ON forum_auth.* TO 'forum'@'%';
GRANT ALL PRIVILEGES ON forum_data.* TO 'forum'@'%';
