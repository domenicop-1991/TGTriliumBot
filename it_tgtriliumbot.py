import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from trilium_py.client import ETAPI
from dotenv import load_dotenv

# Carica il file .env
load_dotenv()

# Recupera le variabili dall'ambiente
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRILIUM_ETAPI_TOKEN = os.getenv("TRILIUM_ETAPI_TOKEN")
TRILIUM_API_URL = os.getenv("TRILIUM_API_URL")

# Configura l'ETAPI di Trilium
trilium_client = ETAPI(TRILIUM_API_URL, TRILIUM_ETAPI_TOKEN)

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variabili in memoria
user_data = {}  # Memorizza dati temporanei per la conversazione


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il comando /start e mostra i pulsanti."""
    chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("Crea Nota", callback_data="crea_nota")],
        [InlineKeyboardButton("Crea Allegato", callback_data="crea_allegato")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=chat_id, text="Benvenuto! Seleziona un'opzione:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i pulsanti."""
    query = update.callback_query
    chat_id = query.message.chat.id

    await query.answer()

    if query.data == "crea_nota":
        user_data[chat_id] = {"action": "crea_nota"}
        await context.bot.send_message(chat_id=chat_id, text="Inserisci il nome della nota:")
    elif query.data == "crea_allegato":
        user_data[chat_id] = {"action": "crea_allegato"}
        await context.bot.send_message(chat_id=chat_id, text="Inserisci il nome dell'allegato:")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce l'input utente dopo aver selezionato un'opzione."""
    chat_id = update.effective_chat.id
    text = update.message.text

    if chat_id not in user_data:
        await context.bot.send_message(chat_id=chat_id, text="Per favore, usa /start per iniziare.")
        return

    action_data = user_data[chat_id]

    if action_data["action"] == "crea_nota":
        if "titolo" not in action_data:  # Primo step: chiedere il titolo della nota
            user_data[chat_id]["titolo"] = text
            await context.bot.send_message(chat_id=chat_id, text="Inserisci il contenuto della nota:")
        else:  # Secondo step: creare la nota
            titolo = user_data[chat_id]["titolo"]
            contenuto = text

            try:
                # Crea la nota con Trilium API
                nota = trilium_client.create_note(parentNoteId="root", title=titolo, content=contenuto, type="text")
                nota_id = nota['note']['noteId']

                await context.bot.send_message(chat_id=chat_id,
                                               text=f"Nota creata con successo!\nID Nota: {nota_id}\nOK.")
            except Exception as e:
                logger.error(f"Errore nella creazione della nota: {e}")
                await context.bot.send_message(chat_id=chat_id, text="Errore durante la creazione della nota!")
            finally:
                del user_data[chat_id]

    elif action_data["action"] == "crea_allegato":
        if "titolo" not in action_data:  # Primo step: chiedere il titolo dell'allegato
            user_data[chat_id]["titolo"] = text
            await context.bot.send_message(chat_id=chat_id, text="Allega il file ora.")
        else:  # In attesa del file per l'allegato
            await context.bot.send_message(chat_id=chat_id, text="Per favore invia un file, non un testo!")


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i file allegati dall'utente."""
    chat_id = update.effective_chat.id
    document = update.message.document

    if chat_id not in user_data or user_data[chat_id]["action"] != "crea_allegato":
        await context.bot.send_message(chat_id=chat_id, text="Per favore, usa /start per iniziare.")
        return

    titolo = user_data[chat_id]["titolo"]

    # Scaricare il file
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()

    # Creazione del percorso temporaneo
    temp_file_path = f"/tmp/{document.file_name}"

    try:
        # Salva localmente il file
        with open(temp_file_path, "wb") as f:
            f.write(file_content)

        # Cerca la nota "FromTelegram"
        results = trilium_client.search_note(search="FromTelegram")
        if results['results']:
            parent_id = results['results'][0]['noteId']

            # Crea allegato
            attachment = trilium_client.create_attachment(
                ownerId=parent_id,
                file_path=temp_file_path
            )
            logger.info(f"Risposta API create_attachment: {attachment}")
            attachment_id = attachment['note']['noteId']  # Correzione: utilizzo corretto di noteId

            # Aggiorna il contenuto della nota
            note_content = trilium_client.get_note_content(parent_id)
            attachment_url = f"/api/attachments/{attachment_id}"
            updated_content = f"{note_content}\n![{document.file_name}]({attachment_url})"
            trilium_client.update_note_content(parent_id, updated_content)

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Allegato caricato con successo!\nID Allegato: {attachment_id}\nOK."
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text="La nota 'FromTelegram' non è stata trovata.")
    except Exception as e:
        logger.error(f"Errore nel caricamento dell'allegato: {e}")
        await context.bot.send_message(chat_id=chat_id, text="La nota è stata creata, la trovi nell'elenco di allegati della nota FromTelegram")
    finally:
        # Rimuovi il file temporaneo
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        del user_data[chat_id]


# Configura l'Application per il bot Telegram
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

# Aggiunta dei gestori
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

# Avvio del bot
if __name__ == "__main__":
    app.run_polling()
