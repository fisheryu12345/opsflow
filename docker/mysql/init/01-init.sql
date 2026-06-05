-- ============================================================
-- OPSflow MySQL initialization
-- ============================================================
-- This runs on first container start to ensure the database
-- uses utf8mb4 encoding (required for Chinese characters).
-- ============================================================

ALTER DATABASE opsflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
