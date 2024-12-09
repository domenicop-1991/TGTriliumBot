##BASE64 file upload is broken as fuck

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from trilium_py.client import ETAPI
from dotenv import load_dotenv
import base64
import mimetypes  # Import necessario per determinare il MIME type

# Carica il file .env
load_dotenv()

# Recupera le variabili dall'ambiente
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRILIUM_ETAPI_TOKEN = os.getenv("TRILIUM_ETAPI_TOKEN")
TRILIUM_API_URL = os.getenv("TRILIUM_API_URL")

# Configura l'ETAPI di Trilium
trilium_client = ETAPI(TRILIUM_API_URL, TRILIUM_ETAPI_TOKEN)
print(trilium_client)

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variabili in memoria
user_data = {}  # Memorizza dati temporanei per la conversazione


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il comando /start e mostra i pulsanti."""
    chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("New note", callback_data="crea_nota")],
        [InlineKeyboardButton("New attachment", callback_data="crea_allegato")]
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
                                               text=f"La nota è stata creata!\n\nNoteID: {nota_id}")
            except Exception as e:
                logger.error(f"Errore nella creazione della nota: {e}")
                await context.bot.send_message(chat_id=chat_id, text="Errore! \n\nLa nota potrebbe non essere stata creata.")
            finally:
                del user_data[chat_id]

    elif action_data["action"] == "crea_allegato":
        if "titolo" not in action_data:  # Primo step: chiedere il titolo dell'allegato
            user_data[chat_id]["titolo"] = text
            await context.bot.send_message(chat_id=chat_id, text="Inviami ora il file (le immagini devono essere inviate senza compressione).")
        else:  # In attesa del file per l'allegato
            await context.bot.send_message(chat_id=chat_id, text="Per favore, invia un file, non del testo!")

# Funzione per gestire i file allegati dall'utente
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
    file_name = document.file_name

    # Determina il MIME type del file utilizzando mimetypes
    mime_type, _ = mimetypes.guess_type(file_name)
    if not mime_type:
        mime_type = document.mime_type or 'application/octet-stream'

    # Imposta il 'type' in base al MIME type
    if mime_type.startswith('image/'):
        note_type = 'image'
    elif mime_type.startswith('text/'):
        note_type = 'code'
    else:
        note_type = 'file'

    # Codifica il contenuto del file in base64
    encoded_content = base64.b64encode(file_content).decode('utf-8')

    try:
        # Cerca la nota "FromTelegram"
        results = trilium_client.search_note(search="FromTelegram")
        if results['results']:
            parent_id = results['results'][0]['noteId']

            # Crea l'allegato come una nuova nota con il tipo corretto
            attachment = trilium_client.create_note(
                parentNoteId=parent_id,
                title=titolo,
                type=note_type,
                mime=mime_type,
                content=encoded_content
            )
            attachment_id = attachment['note']['noteId']

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Allegato caricato con successo!\nID Allegato: {attachment_id}\nLo trovi nella nota 'FromTelegram'."
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text="La nota 'FromTelegram' non è stata trovata.")
    except Exception as e:
        logger.error(f"Errore nel caricamento dell'allegato: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Errore durante il caricamento dell'allegato.")
    finally:
        # Rimuovi i dati dell'utente
        del user_data[chat_id]


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce le foto inviate dall'utente."""
    chat_id = update.effective_chat.id
    photos = update.message.photo

    if chat_id not in user_data or user_data[chat_id]["action"] != "crea_allegato":
        await context.bot.send_message(chat_id=chat_id, text="Per favore, usa /start per iniziare.")
        return

    titolo = user_data[chat_id]["titolo"]

    # Ottiene la foto con la risoluzione più alta
    photo = photos[-1]
    file = await context.bot.get_file(photo.file_id)
    file_content = await file.download_as_bytearray()
    file_name = f"{titolo}.jpg"  # Puoi utilizzare un'estensione appropriata
    mime_type = 'image/jpeg'
    note_type = 'image'

    # Codifica il contenuto del file in base64
    encoded_content = base64.b64encode(file_content).decode('utf-8')

    try:
        # Cerca la nota "FromTelegram"
        results = trilium_client.search_note(search="FromTelegram")
        if results['results']:
            parent_id = results['results'][0]['noteId']

            # Crea l'allegato come una nuova nota con il tipo corretto
            attachment = trilium_client.create_note(
                parentNoteId=parent_id,
                title=titolo,
                type=note_type,
                mime=mime_type,
                content=encoded_content
            )
            attachment_id = attachment['note']['noteId']

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Immagine caricata con successo!\nID Allegato: {attachment_id}\nLo trovi nella nota 'FromTelegram'."
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text="La nota 'FromTelegram' non è stata trovata.")
    except Exception as e:
        logger.error(f"Errore nel caricamento dell'immagine: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Errore durante il caricamento dell'immagine.")
    finally:
        # Rimuovi i dati dell'utente
        del user_data[chat_id]


# Configura l'Application per il bot Telegram
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

# Aggiunta dei gestori
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

# Avvio del bot
if __name__ == "__main__":
    app.run_polling()
