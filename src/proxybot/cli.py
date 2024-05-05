"CLI interface for proxybot." ""

from __future__ import annotations

import logging
import os
from typing import Optional


from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    MessageReactionHandler,
    filters,
)
from telegram.ext.filters import MessageFilter

from proxybot.db import setup_db, get_db

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def unpack_optional[T](opt: Optional[T]) -> T:
    if opt is None:
        raise ValueError("Optional value is None")
    return opt


GROUP_CHATID = unpack_optional(os.environ.get("BOT_GROUPID"))
TOKEN = unpack_optional(os.environ.get("BOT_TOKEN"))

USER_MESSAGE_FILTER = (
    filters.ALL
    & (~filters.COMMAND)
    & (~filters.Chat(int(GROUP_CHATID)))
    & filters.ChatType.PRIVATE
)


class GroupMessageFilter(MessageFilter):
    def filter(self, message):
        return (
            (message is not None)
            and (filters.ALL).filter(message)
            and (message.chat.id == GROUP_CHATID)
            and (message.reply_to_message is not None)
        )


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    assert update.message is not None
    if (
        update.effective_user is not None
        and (user := update.effective_user)
        and user.id > 0
    ):
        await update.message.reply_html(
            rf"Hi! {user.mention_html()}, Conversation with this bot is send to our admins.",
            reply_markup=ForceReply(selective=True),
        )


async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    assert update.message is not None
    if update.message:
        await update.message.reply_text("Help!")


async def forward_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = get_db()
    assert update.message_reaction
    message_id = update.message_reaction.message_id
    query = db.cursor().execute(
        "select user_id, dm_message_id from forwards where message_id = ?",
        (message_id,),
    )
    res: Optional[tuple[str, str]] = query.fetchone()
    if res is not None:
        (user_id, dm_message_id) = res
        await context.bot.set_message_reaction(
            user_id, int(dm_message_id), update.message_reaction.new_reaction
        )


async def group_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = get_db()
    assert update.message
    replied_to_message = update.message.reply_to_message
    assert replied_to_message is not None
    query = db.cursor().execute(
        "select user_id, dm_message_id from forwards where message_id = ?",
        (replied_to_message.id,),
    )
    res: Optional[tuple[str, str]] = query.fetchone()
    if res is not None:
        (user_id, _) = res
        await context.bot.copy_message(
            user_id,
            GROUP_CHATID,
            update.message.id,
        )


async def user_forward(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    db = get_db()
    assert update.message
    chat_id = update.message.chat.id
    message = await update.message.forward(GROUP_CHATID)
    db.cursor().execute(
        "INSERT INTO forwards values (?, ?, ?)",
        (message.id, chat_id, update.message.id),
    )
    db.commit()


def cli() -> None:
    """Start the bot."""
    setup_db()

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    groupfilter = GroupMessageFilter()

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(groupfilter, group_forward))
    application.add_handler(MessageHandler(USER_MESSAGE_FILTER, user_forward))
    application.add_handler(
        MessageReactionHandler(forward_reaction, chat_id=int(GROUP_CHATID))
    )
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
