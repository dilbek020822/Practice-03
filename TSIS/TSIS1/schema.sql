-- ============================================================
--  PhoneBook  –  Extended Schema  (Practice 9)
--  Extends the base contacts table from Practice 7/8
-- ============================================================

-- 1. Groups / categories
CREATE TABLE IF NOT EXISTS groups (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- Seed default categories
INSERT INTO groups (name) VALUES
    ('Family'),
    ('Work'),
    ('Friend'),
    ('Other')
ON CONFLICT (name) DO NOTHING;

-- 2. Contacts  (base table already exists; add new columns)
CREATE TABLE IF NOT EXISTS contacts (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE contacts
    ADD COLUMN IF NOT EXISTS email    VARCHAR(100),
    ADD COLUMN IF NOT EXISTS birthday DATE,
    ADD COLUMN IF NOT EXISTS group_id INTEGER REFERENCES groups(id);

-- 3. Phones  –  1-to-many per contact
CREATE TABLE IF NOT EXISTS phones (
    id         SERIAL PRIMARY KEY,
    contact_id INTEGER      NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    phone      VARCHAR(20)  NOT NULL,
    type       VARCHAR(10)  NOT NULL DEFAULT 'mobile'
                            CHECK (type IN ('home', 'work', 'mobile'))
);

-- Migrate existing single-phone column into the phones table (safe to run
-- multiple times because of the WHERE NOT EXISTS guard).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE  table_name = 'contacts' AND column_name = 'phone'
    ) THEN
        INSERT INTO phones (contact_id, phone, type)
        SELECT id, phone, 'mobile'
        FROM   contacts
        WHERE  phone IS NOT NULL
          AND  NOT EXISTS (
                   SELECT 1 FROM phones p WHERE p.contact_id = contacts.id
               );
    END IF;
END
$$;

-- Indexes for fast filtering / searching
CREATE INDEX IF NOT EXISTS idx_phones_contact ON phones(contact_id);
CREATE INDEX IF NOT EXISTS idx_contacts_group  ON contacts(group_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email  ON contacts(email);
