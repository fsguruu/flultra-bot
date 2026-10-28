"""
Production texts (English, clean).
Used by default and whenever bot_msgs_local.py is missing.
Every key here must also exist in bot_msgs_local.py (local re-imports this file, so missing keys fall back here).
"""

### DB (console logs)

DB_USER_REGISTER_ERR = "❌ Database error when registering a user."
DB_USERS_RECIEVING_ERR = "❌ Database error when receiving users."

### START

START_RESPONSE = ("👋 Hi! To use this bot you need an activation key starting with \"FLU_\".\n"
                  "To get one, contact @bldslr.")

### AUTH

SLASH_CANCEL_RESPONSE = "Bot activation has been cancelled."
WAITING_FOR_KEY_STATE = "⏳ Waiting for the key. It starts with \"FLU_\"."
GROUP_REGISTERED_SUCCESS = ("✅ This chat has been activated.\n"
                            "I'll fetch all Instagram / TikTok / YouTube Shorts links sent by members of this chat.")
PRIVATE_REGISTERED_SUCCESS = "✅ The bot has been activated. Send me an Instagram / TikTok / YouTube Shorts link."
INVALID_KEY = "❌ Invalid key. If you don't have one, type /cancel."
LOGIN_ADMINS_ONLY = "⛔ Only chat admins can activate the bot in a group."

### MEDIA

ANALYZING_LINK = "🔄 Analyzing the link..."
CRITICAL_PROCESSING_ERR = "❌ A critical error occurred while processing the link."

# {tag} - platform tag: IG / TT / YT
DOWNLOADING = "[{tag}] Downloading..."
DOWNLOADING_SECOND = "[{tag}] Downloading via a backup service..."
DOWNLOADING_THIRD = "[{tag}] Downloading via the last backup service..."

IG_DOWNLOAD_FAILED = "❌ [IG] Couldn't download this reel/post (it may be private or deleted)."
TT_DOWNLOAD_FAILED = "❌ [TikTok] Couldn't download this TikTok (it may be private or deleted)."
YT_DOWNLOAD_FAILED = "❌ [YT] Couldn't download this Short (it may be private or deleted)."

CAROUSEL_ALL_FAILED = "❌ Couldn't download any of the slides."
SEND_FAILED = "❌ Telegram rejected the file, it may be too large (>50 MB)."

# {url} - original link
CAPTION_HEADER = "<a href='{url}'>Open</a> \\ via @FLUltrabot"
CAPTION_TRUNCATED_SUFFIX = "..."

### ADMIN: KEYS

# {key} - generated key
NEW_KEY_GENERATED = "🔑 New activation key generated: <code>{key}</code>"

TIMEOUT_USAGE = ("Specify the key to deactivate.\n"
                 "Example: <code>/timeout FLU_12345678</code> or <code>/out FLU_12345678</code>")
# {key}
KEY_TIMED_OUT = ("Key <code>{key}</code> has been deactivated.\n"
                 "The chat/user no longer has access to the bot, and the key can't be used again.")

REVIVE_USAGE = ("Specify the key to reactivate.\n"
                "Example: <code>/revive FLU_12345678</code> or <code>/rev FLU_12345678</code>")
# {key}
KEY_REVIVED = ("Key <code>{key}</code> is active again.\n"
               "The chat/user has access to the bot again.")

KEY_NOT_FOUND = "This key doesn't exist in the database."

KEYS_TITLE = "List of <b>active</b> and <b>free</b> keys:"
DEADKEYS_TITLE = "<b>List of revoked keys:</b>"
# {title}
KEYS_EMPTY = "{title}\n\nThe list is empty. Generate a key with /newkey (or /genkey, /nk, /gk)."

KEY_STATUS_FREE = "🟢 Free"
# {chat_id}, {username}
KEY_STATUS_ACTIVE = "🔴 In use (chat: <code>{chat_id}</code> | activated by: {username})"
KEY_STATUS_REVOKED = "Was used in: <code>{chat_id}</code> | activated by: {username}"
KEY_NO_NOTE = "No note"
KEYS_LIST_TRUNCATED = "\n\n<i>... The list is too long, not all keys are shown.</i>"

### ADMIN: IDS

# {user_id}, {chat_id}, {chat_type}
IDS_INFO = ("Your User ID: <code>{user_id}</code>\n"
            "Chat ID: <code>{chat_id}</code>\n"
            "Chat type: <code>{chat_type}</code>")

### LOGS

TAG_ALL_SEND_ERR = "❌ Failed to send @all."
