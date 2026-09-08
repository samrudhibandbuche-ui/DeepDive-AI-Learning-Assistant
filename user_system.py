import hashlib
import hmac
import os
import sqlite3
from datetime import date, timedelta

DATABASE = "users.db"


def get_connection():
    return sqlite3.connect(DATABASE)


def create_users_table():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 100,
            streak INTEGER NOT NULL DEFAULT 0,
            last_active TEXT,
            badges TEXT NOT NULL DEFAULT ''
        )
        """
    )

    # Add new columns to an older users.db created by the first version.
    existing_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()
    }

    migrations = {
        "xp": "ALTER TABLE users ADD COLUMN xp INTEGER NOT NULL DEFAULT 100",
        "streak": "ALTER TABLE users ADD COLUMN streak INTEGER NOT NULL DEFAULT 0",
        "last_active": "ALTER TABLE users ADD COLUMN last_active TEXT",
        "badges": "ALTER TABLE users ADD COLUMN badges TEXT NOT NULL DEFAULT ''",
    }

    for column, statement in migrations.items():
        if column not in existing_columns:
            cursor.execute(statement)

    connection.commit()
    connection.close()


def hash_password(password):
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 100_000
    )
    return f"{salt.hex()}:{password_hash.hex()}"


def verify_password(password, stored_password):
    try:
        salt_hex, hash_hex = stored_password.split(":", 1)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False

    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 100_000
    )
    return hmac.compare_digest(password_hash.hex(), hash_hex)


def create_account(username, password):
    username = username.strip()

    if not username or not password:
        return False, "Username and password are required."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    password_hash = hash_password(password)
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, xp, streak, badges)
            VALUES (?, ?, 100, 0, '')
            """,
            (username, password_hash),
        )
        connection.commit()
        return True, "Account created successfully! You received 100 XP."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        connection.close()


def login_user(username, password):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, username, password_hash, xp, streak, last_active, badges
        FROM users
        WHERE username = ?
        """,
        (username.strip(),),
    )
    user = cursor.fetchone()
    connection.close()

    if user is None:
        return None

    user_id, username, stored_password, xp, streak, last_active, badges = user

    if not verify_password(password, stored_password):
        return None

    return {
        "id": user_id,
        "username": username,
        "xp": xp,
        "streak": streak,
        "last_active": last_active,
        "badges": [badge for badge in (badges or "").split(",") if badge],
    }


def get_user(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, username, xp, streak, last_active, badges FROM users WHERE id = ?",
        (user_id,),
    )
    user = cursor.fetchone()
    connection.close()

    if user is None:
        return None

    user_id, username, xp, streak, last_active, badges = user
    return {
        "id": user_id,
        "username": username,
        "xp": xp,
        "streak": streak,
        "last_active": last_active,
        "badges": [badge for badge in (badges or "").split(",") if badge],
    }


def calculate_level(xp):
    return (max(0, xp) // 200) + 1


def xp_progress(xp):
    level = calculate_level(xp)
    current_level_xp = (level - 1) * 200
    next_level_xp = level * 200
    return xp - current_level_xp, next_level_xp - current_level_xp


def _badge_list_to_text(badges):
    return ",".join(dict.fromkeys(badges))


def award_xp(user_id, amount, badge=None):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT xp, badges FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        connection.close()
        return None

    xp, badges_text = row
    badges = [item for item in (badges_text or "").split(",") if item]
    xp += max(0, int(amount))

    if badge and badge not in badges:
        badges.append(badge)

    cursor.execute(
        "UPDATE users SET xp = ?, badges = ? WHERE id = ?",
        (xp, _badge_list_to_text(badges), user_id),
    )
    connection.commit()
    connection.close()

    return get_user(user_id)


def record_activity(user_id):
    """Update the daily study streak once per calendar day."""
    today = date.today()

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT streak, last_active FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        connection.close()
        return None

    streak, last_active = row

    if last_active == today.isoformat():
        connection.close()
        return get_user(user_id)

    if last_active:
        try:
            previous_day = date.fromisoformat(last_active)
        except ValueError:
            previous_day = None
    else:
        previous_day = None

    if previous_day == today - timedelta(days=1):
        streak += 1
    else:
        streak = 1

    cursor.execute(
        "UPDATE users SET streak = ?, last_active = ? WHERE id = ?",
        (streak, today.isoformat(), user_id),
    )
    connection.commit()
    connection.close()

    if streak >= 7:
        return award_xp(user_id, 0, "7 Day Streak")

    return get_user(user_id)


create_users_table()


if __name__ == "__main__":
    print("Database and users table are ready!")
