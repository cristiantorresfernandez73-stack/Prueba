CREATE DATABASE IF NOT EXISTS tft_meta
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE tft_meta;

CREATE TABLE IF NOT EXISTS meta_snapshots (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  season VARCHAR(32) NOT NULL,
  patch VARCHAR(32) NOT NULL,
  region VARCHAR(64) NOT NULL,
  rank_label VARCHAR(64) NOT NULL,
  checked_at DATE NOT NULL,
  source_url VARCHAR(512) NOT NULL,
  compositions JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_meta_snapshots_created_at (created_at)
) ENGINE=InnoDB;