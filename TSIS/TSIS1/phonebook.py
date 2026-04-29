"""
phonebook.py  –  PhoneBook Console Application (Practice 9)
============================================================
Extends Practice 7 & 8 with:
  • Relational schema  (phones table, groups table, email, birthday)
  • Filter by group, search by email, sort options
  • Paginated navigation (next / prev / quit)
  • JSON export & import with duplicate handling
  • Extended CSV import (email, birthday, group, phone type)
  • Stored procedures: add_phone, move_to_group, search_contacts
"""
import io

# Принудительно переключаем вывод в UTF-8

import csv
import json
import os
import sys
from datetime import date, datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from connect import get_connection, get_cursor

# ──────────────────────────────────────────────────────────────
# Pretty-print helpers
# ──────────────────────────────────────────────────────────────
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
SEP  = "─" * 70
SEP2 = "═" * 70

def _header(title: str):
    print(f"\n{SEP2}\n  {title}\n{SEP2}")

def _row(label: str, value):
    print(f"  {label:<18} {value}")

def _print_contact(row: dict):
    """Print one contact record (from search_contacts or full-view queries)."""
    print(SEP)
    _row("Name:",      row.get("full_name") or row.get("name", "—"))
    _row("Email:",     row.get("email") or "—")
    _row("Birthday:",  row.get("birthday") or "—")
    _row("Group:",     row.get("group_name") or "—")
    _row("Phones:",    row.get("phones") or "—")
    _row("Added:",     str(row.get("created_at", ""))[:19])

def _print_contacts(rows):
    if not rows:
        print("  (no contacts found)")
        return
    for r in rows:
        _print_contact(r)
    print(SEP)
    print(f"  {len(rows)} contact(s) shown.")


# ──────────────────────────────────────────────────────────────
# Schema bootstrap  (idempotent – safe to call every run)
# ──────────────────────────────────────────────────────────────
def bootstrap_schema(conn):
    """Apply schema.sql and procedures.sql if not already applied."""
    base = os.path.dirname(os.path.abspath(__file__))
    with conn.cursor() as cur:
        for fname in ("schema.sql", "procedures.sql"):
            fpath = os.path.join(base, fname)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    cur.execute(f.read())
    conn.commit()
    print("✔  Schema and procedures loaded.")


# ──────────────────────────────────────────────────────────────
# 3.4 – Stored procedure wrappers
# ──────────────────────────────────────────────────────────────
def db_add_phone(conn, contact_name: str, phone: str, phone_type: str):
    with conn.cursor() as cur:
        cur.execute(
            "CALL add_phone(%s, %s, %s);",
            (contact_name, phone, phone_type),
        )
    conn.commit()


def db_move_to_group(conn, contact_name: str, group_name: str):
    with conn.cursor() as cur:
        cur.execute(
            "CALL move_to_group(%s, %s);",
            (contact_name, group_name),
        )
    conn.commit()


def db_search_contacts(conn, query: str) -> list[dict]:
    with get_cursor(conn) as cur:
        cur.execute("SELECT * FROM search_contacts(%s);", (query,))
        return cur.fetchall()


# ──────────────────────────────────────────────────────────────
# Helper: resolve or create a group, return its id
# ──────────────────────────────────────────────────────────────
def _resolve_group(cur, group_name: str) -> int | None:
    if not group_name:
        return None
    cur.execute(
        "SELECT id FROM groups WHERE LOWER(name) = LOWER(%s);",
        (group_name,),
    )
    row = cur.fetchone()
    if row:
        return row[0] if isinstance(row, tuple) else row["id"]
    cur.execute(
        "INSERT INTO groups (name) VALUES (%s) RETURNING id;",
        (group_name,),
    )
    row = cur.fetchone()
    return row[0] if isinstance(row, tuple) else row["id"]


# ──────────────────────────────────────────────────────────────
# 3.3 – CSV import (extended)
# ──────────────────────────────────────────────────────────────
def import_csv(conn, filepath: str):
    """
    Import contacts from CSV.
    Expected columns: name, phone, phone_type, email, birthday, group
    phone_type: home | work | mobile   (defaults to 'mobile' if missing)
    birthday:   YYYY-MM-DD             (optional)
    """
    if not os.path.exists(filepath):
        print(f"  ✗  File not found: {filepath}")
        return

    inserted = skipped = 0
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with conn.cursor() as cur:
            for row in reader:
                name       = (row.get("name") or "").strip()
                phone      = (row.get("phone") or "").strip()
                phone_type = (row.get("phone_type") or "mobile").strip().lower()
                email      = (row.get("email") or "").strip() or None
                birthday_s = (row.get("birthday") or "").strip()
                group_name = (row.get("group") or "").strip()

                if not name:
                    skipped += 1
                    continue

                if phone_type not in ("home", "work", "mobile"):
                    phone_type = "mobile"

                birthday = None
                if birthday_s:
                    try:
                        birthday = datetime.strptime(birthday_s, "%Y-%m-%d").date()
                    except ValueError:
                        pass

                group_id = _resolve_group(cur, group_name) if group_name else None

                # Upsert contact (by name)
                cur.execute("""
                    INSERT INTO contacts (name, email, birthday, group_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id;
                """, (name, email, birthday, group_id))
                result = cur.fetchone()

                if result is None:
                    # Contact exists – fetch its id
                    cur.execute("SELECT id FROM contacts WHERE LOWER(name)=LOWER(%s);", (name,))
                    result = cur.fetchone()
                    contact_id = result[0] if isinstance(result, tuple) else result["id"]
                else:
                    contact_id = result[0] if isinstance(result, tuple) else result["id"]

                # Insert phone if provided and not duplicate
                if phone:
                    cur.execute("""
                        INSERT INTO phones (contact_id, phone, type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING;
                    """, (contact_id, phone, phone_type))

                inserted += 1

    conn.commit()
    print(f"  ✔  CSV import done: {inserted} processed, {skipped} skipped.")


# ──────────────────────────────────────────────────────────────
# 3.3 – JSON export
# ──────────────────────────────────────────────────────────────
def export_json(conn, filepath: str = "contacts_export.json"):
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT
                c.id,
                c.name,
                c.email,
                c.birthday::TEXT,
                g.name AS group_name,
                c.created_at::TEXT,
                JSON_AGG(
                    JSON_BUILD_OBJECT('phone', ph.phone, 'type', ph.type)
                    ORDER BY ph.type
                ) FILTER (WHERE ph.id IS NOT NULL) AS phones
            FROM  contacts c
            LEFT  JOIN groups g  ON g.id  = c.group_id
            LEFT  JOIN phones ph ON ph.contact_id = c.id
            GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at
            ORDER BY c.name;
        """)
        rows = cur.fetchall()

    # Convert RealDictRow → plain dict
    data = [dict(r) for r in rows]

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"  ✔  Exported {len(data)} contacts to '{filepath}'.")


# ──────────────────────────────────────────────────────────────
# 3.3 – JSON import
# ──────────────────────────────────────────────────────────────
def import_json(conn, filepath: str = "contacts_export.json"):
    if not os.path.exists(filepath):
        print(f"  ✗  File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    inserted = skipped = overwritten = 0

    with conn.cursor() as cur:
        for record in data:
            name       = (record.get("name") or "").strip()
            email      = record.get("email")
            birthday_s = record.get("birthday")
            group_name = record.get("group_name")
            phones     = record.get("phones") or []

            if not name:
                skipped += 1
                continue

            birthday = None
            if birthday_s:
                try:
                    birthday = datetime.strptime(birthday_s[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass

            group_id = _resolve_group(cur, group_name) if group_name else None

            # Check for existing contact
            cur.execute(
                "SELECT id FROM contacts WHERE LOWER(name)=LOWER(%s);",
                (name,),
            )
            existing = cur.fetchone()

            if existing:
                contact_id = existing[0] if isinstance(existing, tuple) else existing["id"]
                print(f"\n  ⚠  Contact '{name}' already exists.")
                choice = input("     [s]kip  /  [o]verwrite? ").strip().lower()
                if choice == "o":
                    cur.execute("""
                        UPDATE contacts
                        SET email=%(e)s, birthday=%(b)s, group_id=%(g)s
                        WHERE id=%(id)s;
                    """, {"e": email, "b": birthday, "g": group_id, "id": contact_id})
                    # Replace phones
                    cur.execute("DELETE FROM phones WHERE contact_id=%s;", (contact_id,))
                    overwritten += 1
                else:
                    skipped += 1
                    continue
            else:
                cur.execute("""
                    INSERT INTO contacts (name, email, birthday, group_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                """, (name, email, birthday, group_id))
                row = cur.fetchone()
                contact_id = row[0] if isinstance(row, tuple) else row["id"]
                inserted += 1

            for ph in phones:
                phone      = ph.get("phone", "").strip()
                phone_type = ph.get("type", "mobile").strip().lower()
                if phone_type not in ("home", "work", "mobile"):
                    phone_type = "mobile"
                if phone:
                    cur.execute("""
                        INSERT INTO phones (contact_id, phone, type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING;
                    """, (contact_id, phone, phone_type))

    conn.commit()
    print(
        f"\n  ✔  JSON import done: "
        f"{inserted} inserted, {overwritten} overwritten, {skipped} skipped."
    )


# ──────────────────────────────────────────────────────────────
# 3.2 – Filter / sort queries
# ──────────────────────────────────────────────────────────────

SORT_COLUMNS = {
    "1": ("c.name",       "Name"),
    "2": ("c.birthday",   "Birthday"),
    "3": ("c.created_at", "Date Added"),
}

def _base_contact_query() -> str:
    return """
        SELECT
            c.id,
            c.name        AS full_name,
            c.email,
            c.birthday,
            g.name        AS group_name,
            STRING_AGG(
                ph.phone || ' (' || ph.type || ')',
                ', ' ORDER BY ph.type
            )             AS phones,
            c.created_at
        FROM  contacts c
        LEFT  JOIN groups g  ON g.id  = c.group_id
        LEFT  JOIN phones ph ON ph.contact_id = c.id
    """

def list_all_contacts(conn, sort_col: str = "c.name") -> list[dict]:
    sql = (
        _base_contact_query()
        + " GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at"
        + f" ORDER BY {sort_col} NULLS LAST;"
    )
    with get_cursor(conn) as cur:
        cur.execute(sql)
        return cur.fetchall()


def filter_by_group(conn, group_name: str, sort_col: str = "c.name") -> list[dict]:
    sql = (
        _base_contact_query()
        + " WHERE LOWER(g.name) = LOWER(%s)"
        + " GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at"
        + f" ORDER BY {sort_col} NULLS LAST;"
    )
    with get_cursor(conn) as cur:
        cur.execute(sql, (group_name,))
        return cur.fetchall()


def search_by_email(conn, fragment: str, sort_col: str = "c.name") -> list[dict]:
    pattern = f"%{fragment}%"
    sql = (
        _base_contact_query()
        + " WHERE c.email ILIKE %s"
        + " GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at"
        + f" ORDER BY {sort_col} NULLS LAST;"
    )
    with get_cursor(conn) as cur:
        cur.execute(sql, (pattern,))
        return cur.fetchall()


# ──────────────────────────────────────────────────────────────
# 3.2 – Paginated navigation (uses DB function from Practice 8)
# ──────────────────────────────────────────────────────────────
PAGE_SIZE = 5

def paginated_browse(conn):
    """
    Interactive page navigator.  Uses the paginate_contacts DB function
    (defined in Practice 8) if available; falls back to Python slicing.
    """
    _header("Browse Contacts — Paginated")
    sort_col = _pick_sort()
    all_rows = list_all_contacts(conn, sort_col)

    if not all_rows:
        print("  (no contacts)")
        return

    total_pages = max(1, (len(all_rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = 0  # 0-indexed

    while True:
        chunk = all_rows[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
        print(f"\n  Page {page + 1} / {total_pages}")
        _print_contacts(chunk)

        nav = []
        if page > 0:
            nav.append("[p] Prev")
        if page < total_pages - 1:
            nav.append("[n] Next")
        nav.append("[q] Quit")
        cmd = input(f"\n  {' | '.join(nav)}: ").strip().lower()

        if cmd == "n" and page < total_pages - 1:
            page += 1
        elif cmd == "p" and page > 0:
            page -= 1
        elif cmd == "q":
            break
        else:
            print("  Invalid option.")


# ──────────────────────────────────────────────────────────────
# Sort picker (reusable)
# ──────────────────────────────────────────────────────────────
def _pick_sort() -> str:
    print("\n  Sort by:")
    for k, (_, label) in SORT_COLUMNS.items():
        print(f"    [{k}] {label}")
    choice = input("  Choice (default 1 = Name): ").strip()
    col, _ = SORT_COLUMNS.get(choice, ("c.name", "Name"))
    return col


# ──────────────────────────────────────────────────────────────
# CRUD helpers  (add contact, add phone, move group)
# ──────────────────────────────────────────────────────────────
def add_contact(conn):
    _header("Add New Contact")
    name = input("  Name: ").strip()
    if not name:
        print("  ✗  Name is required.")
        return

    email    = input("  Email (optional): ").strip() or None
    bday_str = input("  Birthday YYYY-MM-DD (optional): ").strip()
    birthday = None
    if bday_str:
        try:
            birthday = datetime.strptime(bday_str, "%Y-%m-%d").date()
        except ValueError:
            print("  ⚠  Invalid date format – birthday skipped.")

    # List groups
    with get_cursor(conn) as cur:
        cur.execute("SELECT id, name FROM groups ORDER BY name;")
        groups = cur.fetchall()
    print("\n  Groups:")
    for g in groups:
        print(f"    [{g['id']}] {g['name']}")
    grp_in = input("  Group id (optional): ").strip()
    group_id = int(grp_in) if grp_in.isdigit() else None

    phone      = input("  Phone (optional): ").strip() or None
    phone_type = "mobile"
    if phone:
        phone_type = input("  Phone type (home/work/mobile) [mobile]: ").strip().lower() or "mobile"
        if phone_type not in ("home", "work", "mobile"):
            phone_type = "mobile"

    with conn.cursor() as cur:
        # Check duplicate
        cur.execute("SELECT id FROM contacts WHERE LOWER(name)=LOWER(%s);", (name,))
        if cur.fetchone():
            print(f"  ✗  Contact '{name}' already exists.")
            return

        cur.execute("""
            INSERT INTO contacts (name, email, birthday, group_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (name, email, birthday, group_id))
        contact_id = cur.fetchone()[0]

        if phone:
            cur.execute("""
                INSERT INTO phones (contact_id, phone, type)
                VALUES (%s, %s, %s);
            """, (contact_id, phone, phone_type))

    conn.commit()
    print(f"  ✔  Contact '{name}' added (id={contact_id}).")


def console_add_phone(conn):
    _header("Add Phone to Contact")
    name       = input("  Contact name: ").strip()
    phone      = input("  New phone number: ").strip()
    phone_type = input("  Type (home/work/mobile) [mobile]: ").strip().lower() or "mobile"
    if phone_type not in ("home", "work", "mobile"):
        phone_type = "mobile"
    try:
        db_add_phone(conn, name, phone, phone_type)
        print("  ✔  Done.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"  ✗  {e.pgerror or e}")


def console_move_group(conn):
    _header("Move Contact to Group")
    name  = input("  Contact name: ").strip()
    group = input("  Group name: ").strip()
    try:
        db_move_to_group(conn, name, group)
        print("  ✔  Done.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"  ✗  {e.pgerror or e}")


def delete_contact(conn):
    _header("Delete Contact")
    name = input("  Contact name to delete: ").strip()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM contacts WHERE LOWER(name)=LOWER(%s) RETURNING id;", (name,))
        deleted = cur.fetchone()
    conn.commit()
    if deleted:
        print(f"  ✔  Contact '{name}' deleted.")
    else:
        print(f"  ✗  Contact '{name}' not found.")


# ──────────────────────────────────────────────────────────────
# Console search menus
# ──────────────────────────────────────────────────────────────
def console_search(conn):
    _header("Search Contacts (name / email / phone)")
    query = input("  Search query: ").strip()
    if not query:
        return
    rows = db_search_contacts(conn, query)
    _print_contacts(rows)


def console_filter_group(conn):
    _header("Filter by Group")
    with get_cursor(conn) as cur:
        cur.execute("SELECT name FROM groups ORDER BY name;")
        groups = [r["name"] for r in cur.fetchall()]
    print("  Available groups:", ", ".join(groups))
    group = input("  Group name: ").strip()
    sort  = _pick_sort()
    rows  = filter_by_group(conn, group, sort)
    _print_contacts(rows)


def console_search_email(conn):
    _header("Search by Email")
    fragment = input("  Email fragment (e.g. 'gmail'): ").strip()
    sort     = _pick_sort()
    rows     = search_by_email(conn, fragment, sort)
    _print_contacts(rows)


def console_list_all(conn):
    _header("All Contacts")
    sort = _pick_sort()
    rows = list_all_contacts(conn, sort)
    _print_contacts(rows)


# ──────────────────────────────────────────────────────────────
# Import / Export menus
# ──────────────────────────────────────────────────────────────
def console_export_json(conn):
    _header("Export to JSON")
    path = input("  Output file [contacts_export.json]: ").strip() or "contacts_export.json"
    export_json(conn, path)


def console_import_json(conn):
    _header("Import from JSON")
    path = input("  JSON file [contacts_export.json]: ").strip() or "contacts_export.json"
    import_json(conn, path)


def console_import_csv(conn):
    _header("Import from CSV")
    path = input("  CSV file [contacts.csv]: ").strip() or "contacts.csv"
    import_csv(conn, path)


# ──────────────────────────────────────────────────────────────
# Main menu
# ──────────────────────────────────────────────────────────────
MENU = """
  ┌─────────────────────────────────────────┐
  │           PhoneBook  –  Menu            │
  ├──────┬──────────────────────────────────┤
  │  1   │  List all contacts               │
  │  2   │  Search (name / email / phone)   │
  │  3   │  Filter by group                 │
  │  4   │  Search by email                 │
  │  5   │  Browse paginated                │
  ├──────┼──────────────────────────────────┤
  │  6   │  Add contact                     │
  │  7   │  Add phone to contact            │
  │  8   │  Move contact to group           │
  │  9   │  Delete contact                  │
  ├──────┼──────────────────────────────────┤
  │  10  │  Import from CSV                 │
  │  11  │  Export to JSON                  │
  │  12  │  Import from JSON                │
  ├──────┼──────────────────────────────────┤
  │  0   │  Exit                            │
  └──────┴──────────────────────────────────┘
"""

ACTIONS = {
    "1":  console_list_all,
    "2":  console_search,
    "3":  console_filter_group,
    "4":  console_search_email,
    "5":  paginated_browse,
    "6":  add_contact,
    "7":  console_add_phone,
    "8":  console_move_group,
    "9":  delete_contact,
    "10": console_import_csv,
    "11": console_export_json,
    "12": console_import_json,
}


def main():
    print(SEP2)
    print("  PhoneBook Application  –  Practice 9")
    print(SEP2)

    try:
        conn = get_connection()
    except psycopg2.OperationalError as e:
        print(f"\n  ✗  Cannot connect to database:\n  {e}")
        sys.exit(1)

    # Apply schema & procedures on first run
    try:
        bootstrap_schema(conn)
    except psycopg2.Error as e:
        conn.rollback()
        print(f"  ⚠  Schema bootstrap warning: {e.pgerror or e}")

    while True:
        print(MENU)
        choice = input("  Your choice: ").strip()

        if choice == "0":
            print("\n  Goodbye!\n")
            break

        action = ACTIONS.get(choice)
        if action is None:
            print("  ✗  Invalid option, try again.")
            continue

        try:
            action(conn)
        except psycopg2.Error as e:
            conn.rollback()
            print(f"\n  ✗  Database error: {e.pgerror or e}")
        except KeyboardInterrupt:
            print("\n  (cancelled)")

    conn.close()


if __name__ == "__main__":
    main()
