import json
import logging

from telegram import Update
from telegram.constants import ChatType

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)


from config import (
    BOT_TOKEN,
    NUM_QUESTIONS,
    OWNER_ID,
    PORT,
    WEBHOOK_URL
)


from database import (
    init_database,
    save_user,
    get_user_by_username,
    execute,
    fetchrow
)


from questions import seed_questions


from ai_manager import (
    generate_questions,
    compatibility_analysis
)


from owner_panel import (
    owner_cmd,
    owner_callback,
    maintenance_check
)


logging.basicConfig(
    level=logging.INFO
)

log = logging.getLogger(__name__)



# Active questions in memory
# user_id : session_id/question_index

active_sessions = {}



# -----------------------------
# START
# -----------------------------


async def start_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_chat.type != ChatType.PRIVATE:
        return


    user = update.effective_user


    await save_user(
        user.id,
        user.username,
        user.first_name
    )


    await update.message.reply_text(

        """
سلام 👋

ثبت نامت کامل شد ✅

از این به بعد اگر برای یک قرار کور انتخاب بشی،
ربات همینجا باهات صحبت می‌کنه.

لازم نیست دوباره /start بزنی.
"""

    )



# -----------------------------
# REGISTER GROUP
# -----------------------------


async def register_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_chat.type not in [
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ]:
        return


    admin = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )


    if admin.status not in [
        "administrator",
        "creator"
    ]:

        await update.message.reply_text(
            "فقط ادمین می‌تواند ثبت کند."
        )

        return



    await execute(

        """
        INSERT INTO settings
        (key,value)

        VALUES
        ($1,$2)

        ON CONFLICT(key)

        DO UPDATE SET value=$2
        """,

        f"group_{update.effective_user.id}",

        str(update.effective_chat.id)

    )


    await update.message.reply_text(
        "گروه ثبت شد ✅"
    )



# -----------------------------
# MATCH
# -----------------------------


async def match_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if len(context.args)!=2:

        await update.message.reply_text(
            "استفاده:\n/match @user1 @user2"
        )

        return



    if await maintenance_check(update):
        return



    u1 = await get_user_by_username(
        context.args[0]
    )


    u2 = await get_user_by_username(
        context.args[1]
    )


    if not u1 or not u2:

        await update.message.reply_text(
            "یکی از کاربران هنوز /start نزده."
        )

        return



    questions = await generate_questions(
        NUM_QUESTIONS
    )



    session = await fetchrow(

        """
        INSERT INTO sessions

        (
        group_chat_id,
        admin_id,
        user1_id,
        user2_id,
        questions
        )

        VALUES
        ($1,$2,$3,$4,$5)

        RETURNING id
        """,

        update.effective_chat.id,
        update.effective_user.id,
        u1["telegram_id"],
        u2["telegram_id"],
        json.dumps(questions)

    )


    session_id=session["id"]



    for user in [
        u1["telegram_id"],
        u2["telegram_id"]
    ]:


        active_sessions[user]={
            "session":session_id,
            "index":0
        }


        await context.bot.send_message(

            user,

            f"""
💫 قرار کور شروع شد!

به چند سوال جواب بده.
جواب‌ها ناشناس نمایش داده می‌شوند.

❓ {questions[0]}
"""

        )


    await update.message.reply_text(
        "سوالات ارسال شد ✅"
    )
# -----------------------------
# ANSWERS
# -----------------------------


async def private_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    user_id = update.effective_user.id


    if user_id not in active_sessions:
        return



    state = active_sessions[user_id]


    session_id = state["session"]
    index = state["index"]



    session = await fetchrow(

        """
        SELECT *
        FROM sessions
        WHERE id=$1
        """,

        session_id

    )



    questions=json.loads(
        session["questions"]
    )



    await execute(

        """
        INSERT INTO answers

        (
        session_id,
        user_id,
        question_index,
        answer
        )

        VALUES
        ($1,$2,$3,$4)

        """,

        session_id,
        user_id,
        index,
        update.message.text

    )



    index += 1



    if index < len(questions):

        state["index"]=index


        await update.message.reply_text(
            questions[index]
        )

        return



    del active_sessions[user_id]



    await execute(

        """

        UPDATE sessions

        SET status='waiting'

        WHERE id=$1

        """,

        session_id

    )


    await update.message.reply_text(
        "جواب‌ها ثبت شد ✅ منتظر نفر دوم باش."
    )
# -----------------------------
# MAIN
# -----------------------------


async def startup(app):

    await init_database()

    await seed_questions()

    log.info(
        "Database connected"
    )



def main():


    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(startup)
        .build()
    )


    app.add_handler(
        CommandHandler(
            "start",
            start_cmd
        )
    )


    app.add_handler(
        CommandHandler(
            "register",
            register_cmd
        )
    )


    app.add_handler(
        CommandHandler(
            "match",
            match_cmd
        )
    )


    app.add_handler(
        CommandHandler(
            "owner",
            owner_cmd
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            owner_callback
        )
    )


    app.add_handler(

        MessageHandler(
            filters.TEXT
            &
            ~filters.COMMAND,
            private_message
        )

    )



    if WEBHOOK_URL:


        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL
        )

    else:


        app.run_polling()



if __name__=="__main__":
    main()