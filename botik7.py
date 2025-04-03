from dotenv import load_dotenv
load_dotenv()  # Load .env locally (ignored on Render)

# ===== FAILSAFE CONFIG =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")

ADMIN_ID = int(os.getenv("ADMIN_ID", "1291104906"))  # Fallback to your ID
PORT = int(os.getenv("PORT", "10001"))  # Render-compatible default

# Initialize bot with token validation
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
