"""
Picks the set of bot texts.
BOT_MODE=local in .env -> bot_msgs_local.py (if the file exists), otherwise bot_msgs.py.
Usage: from messages import msgs, IS_LOCAL
"""
import os
from dotenv import load_dotenv

load_dotenv()

IS_LOCAL = False

if os.getenv("BOT_MODE", "prod").strip().lower() == "local":
    try:
        import bot_msgs_local as msgs
        IS_LOCAL = True
    except ImportError:
        print("⚠️ BOT_MODE=local, but bot_msgs_local.py was not found. Using production texts.")
        import bot_msgs as msgs
else:
    import bot_msgs as msgs
