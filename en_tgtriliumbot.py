##LLM translated code from it lang##

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from trilium_py.client import ETAPI
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Retrieve variables from the environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRILIUM_ETAPI_TOKEN = os.getenv("TRILIUM_ETAPI_TOKEN")
TRILIUM_API_URL = os.getenv("TRILIUM_API_URL")

# Configure Trilium's ETAPI
trilium_client = ETAPI(TRILIUM_API_URL, TRILIUM_ETAPI_TOKEN)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory variables
user_data = {}  # Stores temporary data for the conversation


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command and displays the buttons."""
    chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("Create Note", callback_data="create_note")],
        [InlineKeyboardButton("Create Attachment", callback_data="create_attachment")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=chat_id, text="Welcome! Please select an option:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the buttons."""
    query = update.callback_query
    chat_id = query.message.chat.id

    await query.answer()

    if query.data == "create_note":
        user_data[chat_id] = {"action": "create_note"}
        await context.bot.send_message(chat_id=chat_id, text="Enter the name of the note:")
    elif query.data == "create_attachment":
        user_data[chat_id] = {"action": "create_attachment"}
        await context.bot.send_message(chat_id=chat_id, text="Enter the name of the attachment:")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user input after an option has been selected."""
    chat_id = update.effective_chat.id
    text = update.message.text

    if chat_id not in user_data:
        await context.bot.send_message(chat_id=chat_id, text="Please use /start to begin.")
        return

    action_data = user_data[chat_id]

    if action_data["action"] == "create_note":
        if "title" not in action_data:  # First step: ask for the note title
            user_data[chat_id]["title"] = text
            await context.bot.send_message(chat_id=chat_id, text="Enter the content of the note:")
        else:  # Second step: create the note
            title = user_data[chat_id]["title"]
            content = text

            try:
                # Create the note with Trilium API
                note = trilium_client.create_note(parentNoteId="root", title=title, content=content, type="text")
                note_id = note['note']['noteId']

                await context.bot.send_message(chat_id=chat_id,
                                               text=f"Note created successfully!\nNote ID: {note_id}\nOK.")
            except Exception as e:
                logger.error(f"Error creating the note: {e}")
                await context.bot.send_message(chat_id=chat_id, text="Error while creating the note!")
            finally:
                del user_data[chat_id]

    elif action_data["action"] == "create_attachment":
        if "title" not in action_data:  # First step: ask for the attachment title
            user_data[chat_id]["title"] = text
            await context.bot.send_message(chat_id=chat_id, text="Please attach the file now.")
        else:  # Waiting for the file for the attachment
            await context.bot.send_message(chat_id=chat_id, text="Please send a file, not text!")


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles files attached by the user."""
    chat_id = update.effective_chat.id
    document = update.message.document

    if chat_id not in user_data or user_data[chat_id]["action"] != "create_attachment":
        await context.bot.send_message(chat_id=chat_id, text="Please use /start to begin.")
        return

    title = user_data[chat_id]["title"]

    # Download the file
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()

    # Create the temporary path
    temp_file_path = f"/tmp/{document.file_name}"

    try:
        # Save the file locally
        with open(temp_file_path, "wb") as f:
            f.write(file_content)

        # Search for the "FromTelegram" note
        results = trilium_client.search_note(search="FromTelegram")
        if results['results']:
            parent_id = results['results'][0]['noteId']

            # Create attachment
            attachment = trilium_client.create_attachment(
                ownerId=parent_id,
                file_path=temp_file_path
            )
            logger.info(f"API response create_attachment: {attachment}")
            attachment_id = attachment['note']['noteId']  # Correction: correct usage of noteId

            # Update the content of the note
            note_content = trilium_client.get_note_content(parent_id)
            attachment_url = f"/api/attachments/{attachment_id}"
            updated_content = f"{note_content}\n![{document.file_name}]({attachment_url})"
            trilium_client.update_note_content(parent_id, updated_content)

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Attachment uploaded successfully!\nAttachment ID: {attachment_id}\nOK."
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text="The 'FromTelegram' note was not found.")
    except Exception as e:
        logger.error(f"Error uploading the attachment: {e}")
        await context.bot.send_message(chat_id=chat_id, text="The note has been created, you can find it in the attachments list of the 'FromTelegram' note.")
    finally:
        # Remove the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        del user_data[chat_id]


# Configure the Application for the Telegram bot
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

# Add handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

# Start the bot
if __name__ == "__main__":
    app.run_polling()
