import os
import sqlite3
import logging
from datetime import datetime
from aiogram import Router
from messages import msgs

DB_DIR = "data"
DB_NAME = os.path.join(DB_DIR, "main.db")
router = Router()
logger = logging.getLogger(__name__)

def init_db():
    """
    Creates tables when the bot starts, if they don't exist.
    bot_keys - contains bot activation keys;
    chat_members - contains chat members ids and chat ids.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_string TEXT UNIQUE,
            is_active INTEGER DEFAULT 1,
            used_by_user_id INTEGER NULL,
            used_by_username TEXT NULL,
            activated_at DATETIME NULL,
            info TEXT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_members (
                chat_id INTEGER,
                user_id INTEGER,
                full_name TEXT NOT NULL,
                username TEXT,
                PRIMARY KEY (chat_id, user_id)
        )
    """)
    conn.commit()
    conn.close()

def add_member(chat_id: int, user_id: int, full_name: str, username: str):
    """
    Passively adds a user to the database. If he is already there, ignores it.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO chat_members (chat_id, user_id, full_name, username)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, user_id, full_name, username))
        conn.commit()
    except Exception as e:
        logger.error(f"{msgs.DB_USER_REGISTER_ERR}: {e}")
    finally:
        conn.close()

def get_all_members(chat_id: int) -> list[tuple]:
    """
    Returns a list of (user_id, full_name) for a specific chat.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT user_id, full_name
            FROM chat_members
            WHERE chat_id = ?
        ''', (chat_id,))
        result = cursor.fetchall()
        return result
    except Exception as e:
        logger.error(f"{msgs.DB_USERS_RECIEVING_ERR}: {e}")
        return []
    finally:
        conn.close()

######################################################
######################## KEYS ########################
######################################################

def add_key(new_key: str, info: str = None):
    """
    Adds a new generated key to the database.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO bot_keys (key_string, info) VALUES (?, ?)
    """, (new_key, info))

    conn.commit()
    conn.close()

def check_key(key_to_check: str) -> bool:
    """
    Checks if the key exists and is active.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT key_string FROM bot_keys 
        WHERE key_string = ? AND is_active = 1
    """, (key_to_check,))

    result = cursor.fetchone()

    conn.close()
    return bool(result)

def use_key(key_to_use: str, user_id: int, username: str):
    """
    Makes the key inactive and records who used it.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        UPDATE bot_keys 
        SET is_active = 0, used_by_user_id = ?, used_by_username = ?, activated_at = ?
        WHERE key_string = ?
    """, (user_id, username, now, key_to_use))

    conn.commit()
    conn.close()


def is_chat_authorized(chat_id: int) -> bool:
    """
    Checks if there is an ACTIVE (not burned) key in the chat.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM bot_keys 
        WHERE used_by_user_id = ? AND is_active = 0
    """, (chat_id,))

    result = cursor.fetchone()
    conn.close()

    return bool(result)


def timeout_key(key_to_revoke: str) -> bool:
    """
    Removes the right to use the bot by key, but keeps the history.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT key_string FROM bot_keys WHERE key_string = ?", (key_to_revoke,))
    if not cursor.fetchone():
        conn.close()
        return False

    cursor.execute("""
        UPDATE bot_keys
            SET is_active = -1
            WHERE key_string = ?
    """, (key_to_revoke,))

    conn.commit()
    conn.close()
    return True

def revive_key(key_to_revoke: str) -> bool:
    """
    Makes the key active again in the chat it was assigned to.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT key_string FROM bot_keys WHERE key_string = ?", (key_to_revoke,))
    if not cursor.fetchone():
        conn.close()
        return False

    cursor.execute("""
        UPDATE bot_keys
            SET is_active = 0
            WHERE key_string = ?
    """, (key_to_revoke,))

    conn.commit()
    conn.close()
    return True

def get_all_keys(status_filter: str) -> list:
    """
    Returns a list of keys from the database: active or burned.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if status_filter == "active":
        cursor.execute("""SELECT key_string, is_active, used_by_username,
                    used_by_user_id, activated_at, info FROM bot_keys WHERE is_active IN (0, 1)""")
    elif status_filter == "dead":
        cursor.execute("""SELECT key_string, is_active, used_by_username,
                    used_by_user_id, activated_at, info FROM bot_keys WHERE is_active = -1""")

    result = cursor.fetchall()
    conn.close()
    return result