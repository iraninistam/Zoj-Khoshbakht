import os
import json
import sqlite3
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # set this on Render, leave unset for local/Oracle polling
if WEBHOOK_URL:
    WEBHOOK_URL = WEBHOOK_URL.rstrip("/")
PORT = int(os.environ.get("PORT", "10000"))
DB_PATH = os.environ.get("DB_PATH", "blind_date.db")
NUM_QUESTIONS = int(os.environ.get("NUM_QUESTIONS", "6"))

# used only if Gemini question generation fails for some reason
FALLBACK_QUESTIONS = [
    "به چه چیزهایی در زندگی بیشتر از همه اهمیت می‌دی؟",
    "یک روز تعطیل ایده‌آل رو چطور می‌گذرونی؟",
    "چه چیزی توی یک رابطه برات از همه مهم‌تره؟",
    "دنبال چه نوع آدمی برای هم‌صحبتی و رابطه هستی؟",
    "توی بحث یا اختلاف نظر معمولاً چطور رفتار می‌کنی؟",
    "چه چیزی می‌تونه باعث بشه یه رابطه برات جذاب و پایدار بمونه؟",
]

# in-memory active-session tracker: user_id -> {"session_id": int, "q_index": int}
active = {}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        );
        CREATE TABLE IF NOT EXISTS admin_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            group_chat_id INTEGER,
            group_title TEXT
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_chat_id INTEGER,
            admin_id INTEGER,
            user1_id INTEGER,
            user2_id INTEGER,
            user1_done INTEGER DEFAULT 0,
            user2_done INTEGER DEFAULT 0,
            questions_json TEXT,
            status TEXT DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS answers (
            session_id INTEGER,
            user_id INTEGER,
            q_index INTEGER,
            answer TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def upsert_user(telegram_id, username, first_name):
    conn = db()
    conn.execute(
        "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name",
        (telegram_id, username, first_name),
    )
    conn.commit()
    conn.close()


def find_user_by_username(username):
    conn = db()
    row = conn.execute(
        "SELECT telegram_id, first_name FROM users WHERE username = ?", (username.lstrip("@"),)
    ).fetchone()
    conn.close()
    return row


def last_registered_group(admin_id):
    conn = db()
    row = conn.execute(
        "SELECT group_chat_id, group_title FROM admin_groups WHERE admin_id = ? ORDER BY id DESC LIMIT 1",
        (admin_id,),
    ).fetchone()
    conn.close()
    return row


async def call_gemini(prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        log.error(f"Unexpected Gemini response: {data}")
        return ""


async def generate_questions() -> list:
    prompt = (
        f"{NUM_QUESTIONS} تا سوال جالب، متنوع و متفاوت برای یک قرار کور (blind date) به زبان فارسی بنویس. "
        "سوالات باید به آدم‌ها کمک کنن بفهمن چقدر با هم سازگارن (ارزش‌ها، سبک زندگی، شخصیت، انتظارات از رابطه). "
        "فقط و فقط یک آرایه JSON از رشته‌ها برگردون، بدون هیچ توضیح اضافه و بدون Markdown."
    )
    text = await call_gemini(prompt)
    cleaned = text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        questions = json.loads(cleaned)
        if isinstance(questions, list) and all(isinstance(q, str) for q in questions) and questions:
            return questions[:NUM_QUESTIONS]
    except json.JSONDecodeError:
        pass
    log.warning("Falling back to static question list (Gemini question generation failed)")
    return FALLBACK_QUESTIONS[:NUM_QUESTIONS]


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE:
        return
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        "سلام! ثبت‌نام شدی 🎉\n"
        "حالا هر وقت ادمین گروه برای یک قرار کور تو رو انتخاب کنه، همین‌جا باهات صحبت می‌کنم."
    )


async def register_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await update.message.reply_text("این دستور فقط داخل گروه کار می‌کنه.")
        return
    admin_id = update.effective_user.id
    member = await context.bot.get_chat_member(update.effective_chat.id, admin_id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("فقط ادمین گروه می‌تونه این دستور رو اجرا کنه.")
        return

    conn = db()
    conn.execute(
        "INSERT INTO admin_groups (admin_id, group_chat_id, group_title) VALUES (?, ?, ?)",
        (admin_id, update.effective_chat.id, update.effective_chat.title),
    )
    conn.commit()
    conn.close()
    await update.message.reply_text(
        "این گروه ثبت شد ✅ از این به بعد می‌تونی از پیوی ربات دستور /match رو بزنی "
        "تا هیچ‌کس توی گروه نبینه کی رو انتخاب کردی."
    )


async def start_match(context, group_chat_id, admin_id, username1, username2, reply_target):
    u1 = find_user_by_username(username1)
    u2 = find_user_by_username(username2)
    missing = []
    if not u1:
        missing.append(username1)
    if not u2:
        missing.append(username2)
    if missing:
        await reply_target("این کاربر(ها) باید اول توی پیوی ربات دستور /start رو بزنن: " + ", ".join(missing))
        return

    questions = await generate_questions()

    conn = db()
    cur = conn.execute(
        "INSERT INTO sessions (group_chat_id, admin_id, user1_id, user2_id, questions_json) VALUES (?, ?, ?, ?, ?)",
        (group_chat_id, admin_id, u1["telegram_id"], u2["telegram_id"], json.dumps(questions)),
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()

    for uid in (u1["telegram_id"], u2["telegram_id"]):
        active[uid] = {"session_id": session_id, "q_index": 0}
        try:
            await context.bot.send_message(
                uid,
                "سلام! ادمین گروه تو رو برای یک قرار کور انتخاب کرده 💫\n"
                "چند تا سوال می‌پرسم، لطفاً صادقانه جواب بده. هویتت فاش نمیشه، جواب‌هات به صورت ناشناس "
                "(به اسم «نفر اول»/«نفر دوم») به گروه نشون داده میشه.",
            )
            await context.bot.send_message(uid, questions[0])
        except Exception as e:
            log.warning(f"Could not DM user {uid}: {e}")

    await reply_target("سوالات برای هر دو نفر توی پیوی ارسال شد. منتظر جواب‌هاشون می‌مونیم.")


async def match_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id

    if len(context.args) != 2:
        await update.message.reply_text("استفاده درست: /match @username1 @username2")
        return

    if update.effective_chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        member = await context.bot.get_chat_member(update.effective_chat.id, admin_id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("فقط ادمین گروه می‌تونه این دستور رو اجرا کنه.")
            return
        group_chat_id = update.effective_chat.id
        # best-effort: remove the command message so other members don't see who was picked
        try:
            await update.message.delete()
        except Exception as e:
            log.info(f"Could not delete /match message (bot may lack delete permission): {e}")
        await start_match(context, group_chat_id, admin_id, context.args[0], context.args[1], update.effective_chat.send_message)
    elif update.effective_chat.type == ChatType.PRIVATE:
        group = last_registered_group(admin_id)
        if not group:
            await update.message.reply_text(
                "اول باید یک بار توی گروهت دستور /register رو بزنی تا بدونم منظورت کدوم گروهه."
            )
            return
        await start_match(
            context, group["group_chat_id"], admin_id, context.args[0], context.args[1], update.message.reply_text
        )
    else:
        return


async def private_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE:
        return
    user_id = update.effective_user.id
    state = active.get(user_id)
    if not state:
        return  # no active session for this user, ignore

    session_id = state["session_id"]
    q_index = state["q_index"]

    conn = db()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    questions = json.loads(session["questions_json"])

    conn.execute(
        "INSERT INTO answers (session_id, user_id, q_index, answer) VALUES (?, ?, ?, ?)",
        (session_id, user_id, q_index, update.message.text),
    )
    conn.commit()

    q_index += 1
    if q_index < len(questions):
        state["q_index"] = q_index
        await update.message.reply_text(questions[q_index])
        conn.close()
        return

    col = "user1_done" if session["user1_id"] == user_id else "user2_done"
    conn.execute(f"UPDATE sessions SET {col} = 1 WHERE id = ?", (session_id,))
    conn.commit()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    del active[user_id]
    await update.message.reply_text("ممنون! جواب‌هات ثبت شد ✅ منتظر بمون تا طرف مقابل هم سوالاتش رو جواب بده.")

    if session["user1_done"] and session["user2_done"]:
        await post_anonymous_answers_and_verdict(context, session_id)


async def post_anonymous_answers_and_verdict(context: ContextTypes.DEFAULT_TYPE, session_id: int):
    conn = db()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    questions = json.loads(session["questions_json"])
    rows = conn.execute(
        "SELECT user_id, q_index, answer FROM answers WHERE session_id = ? ORDER BY user_id, q_index",
        (session_id,),
    ).fetchall()
    conn.close()

    def answers_for(uid):
        return {r["q_index"]: r["answer"] for r in rows if r["user_id"] == uid}

    a1 = answers_for(session["user1_id"])
    a2 = answers_for(session["user2_id"])

    # post anonymized Q&A to the group — no names, no usernames
    lines = ["🕵️ جواب‌های دو نفر برای قرار کور این هفته (به صورت ناشناس):\n"]
    for i, q in enumerate(questions):
        lines.append(f"❓ {q}")
        lines.append(f"👤 نفر اول: {a1.get(i, '—')}")
        lines.append(f"👤 نفر دوم: {a2.get(i, '—')}\n")
    await context.bot.send_message(session["group_chat_id"], "\n".join(lines))

    # ask Gemini for a compatibility verdict, sent privately to the admin only
    qa_text = "\n".join(
        f"- {q}\n  نفر اول: {a1.get(i, '—')}\n  نفر دوم: {a2.get(i, '—')}" for i, q in enumerate(questions)
    )
    prompt = (
        "شما یک مشاور روابط هستید. بر اساس پاسخ‌های زیر که دو نفر برای یک قرار کور داده‌اند، "
        "تحلیل کوتاهی از سازگاری آن‌ها به زبان فارسی بنویس (حداکثر ۶ خط)، "
        "و در پایان مشخص کن آیا پیشنهاد می‌کنی این دو نفر باهم آشنا بشن یا نه.\n\n" + qa_text
    )
    verdict = await call_gemini(prompt) or "متاسفانه در تحلیل مشکلی پیش اومد."

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ تایید و معرفی در گروه", callback_data=f"approve:{session_id}"),
                InlineKeyboardButton("❌ رد کردن", callback_data=f"reject:{session_id}"),
            ]
        ]
    )
    await context.bot.send_message(
        session["admin_id"],
        f"جواب‌ها به صورت ناشناس توی گروه پست شد. نتیجه تحلیل هوش مصنوعی:\n\n{verdict}",
        reply_markup=keyboard,
    )


async def button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, session_id = query.data.split(":")
    session_id = int(session_id)

    conn = db()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    if action == "approve":
        conn.execute("UPDATE sessions SET status = 'approved' WHERE id = ?", (session_id,))
        conn.commit()
        u1 = await context.bot.get_chat(session["user1_id"])
        u2 = await context.bot.get_chat(session["user2_id"])
        await context.bot.send_message(
            session["group_chat_id"],
            f"🎉 خبر خوب! نفر اول و نفر دوم یک متچ خوب بودن: {u1.mention_html()} و {u2.mention_html()}\n"
            f"حالا نوبت خودتونه که اینجا با هم صحبت کنید 💬",
            parse_mode="HTML",
        )
        await query.edit_message_text("متچ توی گروه اعلام شد و هویت‌ها فاش شدن ✅")
    else:
        conn.execute("UPDATE sessions SET status = 'rejected' WHERE id = ?", (session_id,))
        conn.commit()
        await context.bot.send_message(
            session["group_chat_id"], "این قرار کور به نتیجه نرسید. هویت افراد فاش نمیشه 🤐"
        )
        await query.edit_message_text("رد شد. هویت‌ها همچنان مخفی موندن.")

    conn.close()


def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("register", register_cmd))
    app.add_handler(CommandHandler("match", match_cmd))
    app.add_handler(CallbackQueryHandler(button_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, private_text))

    if WEBHOOK_URL:
        log.info("Starting in webhook mode")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        )
    else:
        log.info("Starting in polling mode")
        app.run_polling()


if __name__ == "__main__":
    main()
