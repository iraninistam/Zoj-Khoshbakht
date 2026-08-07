from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler
)

from config import OWNER_ID
from database import (
    fetch,
    add_log
)

from ai_manager import ask_ai


maintenance_mode = False


def is_owner(user_id):
    return user_id == OWNER_ID



async def owner_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update.effective_user.id):
        return


    users = await fetch(
        "SELECT COUNT(*) FROM users"
    )


    sessions = await fetch(
        """
        SELECT COUNT(*)
        FROM sessions
        WHERE status='active'
        """
    )


    keyboard = InlineKeyboardMarkup(
        [

            [
                InlineKeyboardButton(
                    "🤖 Test AI",
                    callback_data="owner_ai_test"
                ),

                InlineKeyboardButton(
                    "📜 Logs",
                    callback_data="owner_logs"
                )
            ],

            [
                InlineKeyboardButton(
                    "📊 Stats",
                    callback_data="owner_stats"
                ),

                InlineKeyboardButton(
                    "🔧 Maintenance",
                    callback_data="owner_maintenance"
                )
            ]

        ]
    )


    await update.message.reply_text(

        f"""
🤖 Blind Date Bot Control Center


System:
🟢 Bot Online


Users:
{users[0]['count']}


Active Matches:
{sessions[0]['count']}


Maintenance:
{"ON 🔴" if maintenance_mode else "OFF 🟢"}

""",

        reply_markup=keyboard
    )



async def owner_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    if not is_owner(query.from_user.id):
        return



    if query.data == "owner_ai_test":

        await query.edit_message_text(
            "⏳ Testing AI..."
        )


        try:

            response = await ask_ai(
                "Reply only with OK"
            )


            await query.message.reply_text(

                f"""
🤖 AI Test Result:

{"🟢 Working" if response else "🔴 Failed"}

Response:
{response[:200] if response else "No response"}

"""
            )


        except Exception as e:

            await query.message.reply_text(
                f"❌ AI Error:\n{e}"
            )



    elif query.data == "owner_logs":


        logs = await fetch(
            """
            SELECT *
            FROM logs
            ORDER BY created_at DESC
            LIMIT 10
            """
        )


        text="📜 Last Logs:\n\n"


        for log in logs:

            text += (
                f"{log['created_at']}\n"
                f"{log['service']} "
                f"{log['status']}\n"
                f"{log['message']}\n\n"
            )


        await query.message.reply_text(
            text[:4000]
        )



    elif query.data == "owner_stats":


        users = await fetch(
            "SELECT COUNT(*) FROM users"
        )

        matches = await fetch(
            "SELECT COUNT(*) FROM sessions"
        )


        await query.message.reply_text(

            f"""
📊 Statistics


Users:
{users[0]['count']}


Total Matches:
{matches[0]['count']}
"""

        )



    elif query.data == "owner_maintenance":

        global maintenance_mode


        maintenance_mode = not maintenance_mode


        await add_log(
            "SYSTEM",
            "INFO",
            f"Maintenance changed: {maintenance_mode}"
        )


        await query.message.reply_text(

            f"""
🔧 Maintenance Mode:

{"Enabled 🔴" if maintenance_mode else "Disabled 🟢"}

"""

        )



async def maintenance_check(update):

    if maintenance_mode:

        await update.message.reply_text(
            "🔧 Bot is currently under maintenance. Please try again later."
        )

        return True

    return False