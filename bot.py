import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Fetch Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

def process_with_ai(prompt_type: str, user_text: str) -> str:
    """Call Groq API with task-specific system prompts."""
    if not GROQ_API_KEY:
        return "❌ Error: GROQ_API_KEY is not configured in environment variables."

    system_prompts = {
        "paraphrase": "You are a professional editor. Rewrite and paraphrase the provided text to make it clear, engaging, and polished while maintaining original context. Provide only the paraphrased output without extra preamble.",
        "grammar": "You are an expert proofreader. Correct all grammar, spelling, and punctuation errors in the provided text. Provide the corrected version first, followed by a brief bullet-point summary of key corrections if significant changes were made.",
        "summarize": "You are a concise executive assistant. Provide a clean, structured summary with bullet points highlighting the main key takeaways of the input text.",
    }

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompts.get(prompt_type, "Help with the user's text.")},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.3,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if response.status_code == 200:
            return data["choices"][0]["message"]["content"]
        else:
            err = data.get("error", {}).get("message", "AI processing error.")
            return f"❌ Error: {err}"
    except Exception as e:
        logging.error(f"API Request Exception: {e}")
        return "❌ Failed to connect to AI processing engine. Please try again."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✍️ **Welcome to @Quill06_Bot!**\n\n"
        "I am your AI writing assistant for **Paraphrasing**, **Grammar Checking**, and **Summarizing**.\n\n"
        "**Available Commands:**\n"
        "• `/paraphrase <text>` - Rewrite text in a polished, professional voice\n"
        "• `/grammar <text>` - Fix grammar, typos, and formatting\n"
        "• `/summarize <text>` - Summarize long articles or messages\n\n"
        "👉 *Or just send me any raw text message, and choose an action below!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def paraphrase_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Usage: `/paraphrase <your text here>`", parse_mode="Markdown")
        return
    status = await update.message.reply_text("🔄 Paraphrasing text...")
    result = process_with_ai("paraphrase", text)
    await status.edit_text(f"✨ **Paraphrased Version:**\n\n{result}", parse_mode="Markdown")

async def grammar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Usage: `/grammar <your text here>`", parse_mode="Markdown")
        return
    status = await update.message.reply_text("🔍 Checking grammar...")
    result = process_with_ai("grammar", text)
    await status.edit_text(f"📝 **Grammar Correction:**\n\n{result}", parse_mode="Markdown")

async def summarize_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("⚠️ Usage: `/summarize <your text here>`", parse_mode="Markdown")
        return
    status = await update.message.reply_text("📌 Generating summary...")
    result = process_with_ai("summarize", text)
    await status.edit_text(f"📊 **Summary:**\n\n{result}", parse_mode="Markdown")

async def handle_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When raw text is sent without commands, store context and present option buttons."""
    user_text = update.message.text.strip()
    if not user_text:
        return

    context.user_data["pending_text"] = user_text

    keyboard = [
        [
            InlineKeyboardButton("🔄 Paraphrase", callback_data="action_paraphrase"),
            InlineKeyboardButton("🔍 Fix Grammar", callback_data="action_grammar"),
        ],
        [
            InlineKeyboardButton("📌 Summarize Text", callback_data="action_summarize"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "What would you like me to do with this text?",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data.replace("action_", "")
    text = context.user_data.get("pending_text")

    if not text:
        await query.edit_message_text("⚠️ Session expired or text lost. Please send your text again.")
        return

    await query.edit_message_text("⚙️ Processing your text with AI...")
    result = process_with_ai(action, text)

    titles = {
        "paraphrase": "✨ **Paraphrased Version:**",
        "grammar": "📝 **Grammar Correction:**",
        "summarize": "📊 **Summary:**"
    }

    await query.edit_message_text(f"{titles.get(action, '')}\n\n{result}", parse_mode="Markdown")

def main():
    if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
        logging.error("CRITICAL: TELEGRAM_BOT_TOKEN or GROQ_API_KEY environment variable missing!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("paraphrase", paraphrase_cmd))
    app.add_handler(CommandHandler("grammar", grammar_cmd))
    app.add_handler(CommandHandler("summarize", summarize_cmd))

    # Interactive Button Callbacks & Plain Text Handler
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_text))

    logging.info("@Quill06_Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
