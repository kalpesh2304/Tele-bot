import logging
import openai
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackContext, 
    CallbackQueryHandler, filters
)
from voice_gen import generate_voice
from video_gen import generate_avatar_video
from apify_scraper import scrape_twitter_content
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# State management
USER_STATES = {}

async def start(update: Update, context: CallbackContext):
    """Start command with interactive keyboard"""
    keyboard = [
        [InlineKeyboardButton("📝 Direct Script", callback_data='direct')],
        [InlineKeyboardButton("🗒️ Topic + Points", callback_data='topic')],
        [InlineKeyboardButton("🐦 Twitter Handle", callback_data='twitter')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎥 Welcome to VideoBot!\n"
        "Choose your input method:",
        reply_markup=reply_markup
    )

async def handle_button(update: Update, context: CallbackContext):
    """Handle button selections"""
    query = update.callback_query
    await query.answer()
    
    input_type = query.data
    USER_STATES[query.from_user.id] = {'input_type': input_type}
    
    instructions = {
        'direct': "✍️ Please send your full script text (1-2 paragraphs):",
        'topic': "📌 Send your topic followed by bullet points:\nExample:\n'Digital Marketing\n- SEO Importance\n- Social Media Strategies'",
        'twitter': "🔗 Send a Twitter handle (without @)\nExample: 'OpenAI'"
    }
    await query.edit_message_text(text=instructions[input_type])

async def process_content(update: Update, context: CallbackContext):
    """Main processing pipeline with real-time updates"""
    user_id = update.message.from_user.id
    user_state = USER_STATES.get(user_id, {})
    
    if not user_state:
        await update.message.reply_text("⚠️ Please start with /start")
        return

    try:
        # --- PHASE 1: Generate Script ---
        await update.message.reply_text("🔄 Processing your input...")
        
        if user_state['input_type'] == 'twitter':
            handle = update.message.text.strip()
            await update.message.reply_text(f"🔍 Scraping @{handle}'s tweets...")
            tweets = scrape_twitter_content(handle, os.getenv('APIFY_API_KEY'))
            script = generate_gpt_script("\n".join(tweets[:5]))
            
        elif user_state['input_type'] == 'topic':
            prompt = update.message.text
            script = generate_gpt_script(prompt)
            
        else:  # Direct script
            script = update.message.text
        
        # Send script immediately
        await update.message.reply_text(f"📜 Generated Script:\n\n{script}")

        # --- PHASE 2: Generate & Upload Voiceover ---
        # await update.message.reply_text("🔊 Generating and uploading voiceover...")
        # audio_url = generate_voice(
        #     text=script,
        #     eleven_api_key=os.getenv('ELEVEN_LABS_API_KEY'),
        #     heygen_api_key=os.getenv('HEYGEN_API_KEY')
        # )

        # --- PHASE 3: Create Video ---
        await update.message.reply_text("🎞️ Creating video...")
        video_path = generate_avatar_video(
            script,
            api_key=os.getenv('HEYGEN_API_KEY'),
            avatar_id=os.getenv('AVATAR_ID'),
            voice_id=os.getenv('VOICE_ID')
        )
        
        # Send video
        with open(video_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="🎥 Your Custom Video",
                supports_streaming=True
            )

    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
        
    finally:
        # Cleanup (only video file needs cleanup now)
        if 'video_path' in locals() and os.path.exists(video_path):
            os.remove(video_path)
        USER_STATES.pop(user_id, None)

def generate_gpt_script(prompt: str) -> str:
    """Generate script using GPT-4"""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"""Create a 60-second video script using this input:
            {prompt}
            
            Requirements:
            1. Include natural pauses for voiceover
            2. Use simple, conversational language
            3. Add scene descriptions in brackets
            4. Keep under 300 words"""
        }]
    )
    return response.choices[0].message.content.strip()

def main():
    """Start the bot"""
    application = (
        Application.builder()
        .token(os.getenv('TELEGRAM_TOKEN'))
        .job_queue(None)  # Disable JobQueue
        .build()
    )
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_content))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()