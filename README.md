# TgTriliumBot

## Description
This project implements a Telegram bot that allows interaction with [Trilium Notes](https://github.com/zadam/trilium) using its ETAPI. The bot offers functionalities to create notes and upload attachments directly from the chat.

## Main Features
- **Note Creation**: Create new notes in Trilium by specifying the title and content.
- **Attachment Upload**: Upload files as attachment in Trilium, auto-detecting the type of content.
- **Interactive Management**: Uses inline buttons for a better user experience.

## Requirements
- **Python**: 3.11 (the only one i tested with success and definitely not the 3.13 that have wheel issue)
- The following Python libraries (installable via `pip install -r requirements.txt` in the venv):
  - `python-telegram-bot`
  - `python-dotenv`
  - `trilium-py`
- Telegram account and bot token [Telegram Bot API](https://core.telegram.org/bots#botfather)
- Trilium Notes server configured with ETAPI token (API integration enabled)

## Setting up your Telegram bot:

1. **Download the bot script**:
- Download tgtriliumbot.py file and place it in a folder of your choice on your PC

2. **In the same folder create a `.env` file with this voices**:
   ```dotenv
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TRILIUM_ETAPI_TOKEN=your_trilium_token
   TRILIUM_API_URL=your_trilium_api_url
   ```
URL must be include the port of your trilium server (8080 or something else)

3. **start a bash in the folder where you placed the script and**:
   ```bash
   python3.11 -m venv .venv
   ```
   
4. **Activate the virtual enviroment**
   ```bash
   source .venv/bin/activate
   ```
## Execution
Start the bot with the following command:
```bash
python tgtriliumbot.py
```

## Usage
1. Start the bot by sending the `/start` command in the chat with the bot.
2. Use the interactive buttons to:
   - **Create Note**: Enter title and content to create a new note.
   - **Create Attachment**: Provide a file upload an attachment to the "FromTelegram" note in Trilium, if the note not exist it will create for you.

## Code Structure
- `start()`: Shows the main buttons to the user.
- `button_handler()`: Handles interactions with inline buttons.
- `text_handler()`: Collects text for note creation.
- `document_handler()`: Handle file and uncompressed image uploads.

## Future update
1. Photos will be handled by easly sending the compressed photo from telegram and not only as an uncompressed file.
2. Uploading files should generate a new note and then edit it by inserting the attachment. Unfortunately, this point is a bit tricky because by sending the file in base64 it becomes unreadable. 🤨
3. I would like to be able to create a basic search and visualization function.

## Contributions
Contributions to improve the project are welcome. You can open a Pull Request or report issues through the Issues system.

## References
- [Official Trilium Documentation](https://github.com/zadam/trilium) [T0]({})
- [Telegram Bot API](https://core.telegram.org/bots#botfather) [AI KNOWLEDGE]({})
```
