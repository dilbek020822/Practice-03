-- ============================================================
--  PhoneBook  –  Stored Procedures & Functions  (Practice 9)
--  Do NOT duplicate procedures already defined in Practice 8.
-- ============================================================


-- ------------------------------------------------------------
-- 1. add_phone
--    Adds a new phone number to an existing contact by name.
-- ------------------------------------------------------------
CREATE OR REPLACE PROCEDURE add_phone(
    p_contact_name VARCHAR,
    p_phone        VARCHAR,
    p_type         VARCHAR DEFAULT 'mobile'
)
LANGUAGE plpgsql AS $$
DECLARE
    v_contact_id INTEGER;
BEGIN
    -- Validate phone type
    IF p_type NOT IN ('home', 'work', 'mobile') THEN
        RAISE EXCEPTION 'Invalid phone type "%". Must be home, work, or mobile.', p_type;
    END IF;

    -- Resolve contact
    SELECT id INTO v_contact_id
    FROM   contacts
    WHERE  LOWER(name) = LOWER(p_contact_name)
    LIMIT  1;

    IF v_contact_id IS NULL THEN
        RAISE EXCEPTION 'Contact "%" not found.', p_contact_name;
    END IF;

    -- Prevent exact duplicate
    IF EXISTS (
        SELECT 1 FROM phones
        WHERE contact_id = v_contact_id AND phone = p_phone
    ) THEN
        RAISE NOTICE 'Phone % already exists for contact "%". Skipping.', p_phone, p_contact_name;
        RETURN;
    END IF;

    INSERT INTO phones (contact_id, phone, type)
    VALUES (v_contact_id, p_phone, p_type);

    RAISE NOTICE 'Phone % (%) added to contact "%".', p_phone, p_type, p_contact_name;
END;
$$;


-- ------------------------------------------------------------
-- 2. move_to_group
--    Moves a contact to a group; creates the group if absent.
-- ------------------------------------------------------------
CREATE OR REPLACE PROCEDURE move_to_group(
    p_contact_name VARCHAR,
    p_group_name   VARCHAR
)
LANGUAGE plpgsql AS $$
DECLARE
    v_contact_id INTEGER;
    v_group_id   INTEGER;
BEGIN
    -- Resolve (or create) group
    SELECT id INTO v_group_id
    FROM   groups
    WHERE  LOWER(name) = LOWER(p_group_name)
    LIMIT  1;

    IF v_group_id IS NULL THEN
        INSERT INTO groups (name)
        VALUES (p_group_name)
        RETURNING id INTO v_group_id;
        RAISE NOTICE 'Created new group "%".', p_group_name;
    END IF;

    -- Resolve contact
    SELECT id INTO v_contact_id
    FROM   contacts
    WHERE  LOWER(name) = LOWER(p_contact_name)
    LIMIT  1;

    IF v_contact_id IS NULL THEN
        RAISE EXCEPTION 'Contact "%" not found.', p_contact_name;
    END IF;

    UPDATE contacts
    SET    group_id = v_group_id
    WHERE  id       = v_contact_id;

    RAISE NOTICE 'Contact "%" moved to group "%".', p_contact_name, p_group_name;
END;
$$;


-- ------------------------------------------------------------
-- 3. search_contacts  (extends Practice-8 pattern search)
--    Matches against: name, email, AND all phones in phones table.
--    Returns one row per contact (phones collapsed into array).
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION search_contacts(p_query TEXT)
RETURNS TABLE (
    contact_id INTEGER,
    full_name  VARCHAR,
    email      VARCHAR,
    birthday   DATE,
    group_name VARCHAR,
    phones     TEXT,       -- comma-separated list of phone:type pairs
    created_at TIMESTAMP
)
LANGUAGE plpgsql AS $$
DECLARE
    v_pattern TEXT := '%' || p_query || '%';
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.name,
        c.email,
        c.birthday,
        g.name                        AS group_name,
        STRING_AGG(
            ph.phone || ' (' || ph.type || ')',
            ', ' ORDER BY ph.type
        )                             AS phones,
        c.created_at
    FROM  contacts c
    LEFT  JOIN groups g  ON g.id  = c.group_id
    LEFT  JOIN phones ph ON ph.contact_id = c.id
    WHERE
        c.name  ILIKE v_pattern
     OR c.email ILIKE v_pattern
     OR ph.phone ILIKE v_pattern
    GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at
    ORDER BY c.name;
END;
$$;
