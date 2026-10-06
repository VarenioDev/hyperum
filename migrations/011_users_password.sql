ALTER TABLE users ADD COLUMN password_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);