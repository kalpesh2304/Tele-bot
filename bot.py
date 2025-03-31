import os
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler, filters
from dotenv import load_dotenv

from script_gen import generate_script
from voice_gen import generate_voice
from video_gen import generate_avatar_video


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VideoCreatorBot:
    def __init__(self):
        self.user_states = {}

    async def start(self, update: Update, context: CallbackContext) -> None:
        """Handle the /start command"""
        keyboard = [
            [InlineKeyboardButton("📝 Text Input", callback_data='text_input')],
            [InlineKeyboardButton("💡 Video Idea", callback_data='video_idea')],
            [InlineKeyboardButton("🎤 Voice Idea", callback_data='voice_idea')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🎥 Welcome to Video Creator Bot!\nChoose your input method:",
            reply_markup=reply_markup
        )

    async def handle_input_type(self, update: Update, context: CallbackContext) -> None:
        """Handle input type selection"""
        query = update.callback_query
        await query.answer()

        input_type = query.data
        user_id = query.from_user.id

        # Store user state
        self.user_states[user_id] = {'input_type': input_type}

        # Prompt based on input type
        prompts = {
            'text_input': "✍️ Enter your full script or text content:",
            'video_idea': "💡 Describe your video concept:",
            'voice_idea': "🎤 Send a voice message describing your video idea:"
        }

        await query.edit_message_text(text=prompts[input_type])

    async def process_content(self, update: Update, context: CallbackContext) -> None:
        """Process user's content and generate script"""
        user_id = update.message.from_user.id
        user_state = self.user_states.get(user_id)

        if not user_state:
            await update.message.reply_text("⚠️ Please start with /start")
            return

        try:
            # Extract input based on type
            if user_state['input_type'] == 'voice_idea':
                if not update.message.voice:
                    await update.message.reply_text("⚠️ Please send a voice message")
                    return

                voice_file = await update.message.voice.get_file()
                with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
                    await voice_file.download_to_drive(temp_audio.name)
                    # Note: You'd need to add a transcription method here
                    # For now, we'll use a placeholder
                    text_input = "Sample transcribed text"
            else:
                text_input = update.message.text

            # Generate optimized script
            script = generate_script(text_input, user_state['input_type'])

            # Voice generation provider selection
            keyboard = [
                [InlineKeyboardButton("🔊 Eleven Labs", callback_data='eleven_labs')],
                [InlineKeyboardButton("🔈 Deep Labs", callback_data='deep_labs')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Store script for next steps
            context.user_data['script'] = script

            await update.message.reply_text(
                f"✅ Script Generated:\n{script}\n\nChoose voice generation provider:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Content processing error: {e}")
            await update.message.reply_text(f"⚠️ Error processing content: {e}")

    async def handle_voice_provider(self, update: Update, context: CallbackContext) -> None:
        """Handle voice provider selection and generate voice"""
        query = update.callback_query
        await query.answer()

        script = context.user_data.get('script')
        if not script:
            await query.edit_message_text("❌ Script not found. Please restart.")
            return

        provider = query.data
        try:
            # Generate voice based on provider
            if provider == 'eleven_labs':
                voice_path = generate_voice(
                    text=script,
                    provider='eleven_labs',
                    eleven_api_key=os.getenv('ELEVEN_LABS_API_KEY'),
                    voice_id=os.getenv('DEFAULT_ELEVEN_VOICE_ID')
                )
            else:
                voice_path = generate_voice(
                    text=script,
                    provider='deep_labs',
                    base_url=os.getenv('DEEP_LABS_BASE_URL'),
                    ref_audio_id=os.getenv('DEEP_LABS_REF_VOICE_ID')
                )

            # Send voice file
            with open(voice_path, 'rb') as voice_file:
                await query.message.reply_audio(
                    audio=voice_file,
                    caption=f"🎙️ Voice generated using {provider.replace('_', ' ').title()}"
                )

            # Prompt for video generation
            keyboard = [
                [InlineKeyboardButton("🎥 Generate Video", callback_data='generate_video')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Store voice path for next steps
            context.user_data['voice_path'] = voice_path

            await query.message.reply_text(
                "Would you like to generate a video?",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Voice generation error: {e}")
            await query.edit_message_text(f"⚠️ Voice generation failed: {e}")

    async def handle_video_generation(self, update: Update, context: CallbackContext) -> None:
        """Generate video from voice"""
        query = update.callback_query
        await query.answer()

        voice_path = context.user_data.get('voice_path')
        script = context.user_data.get('script')

        if not voice_path or not script:
            await query.edit_message_text("❌ Missing voice or script. Please restart.")
            return

        try:
            # Generate video
            video_path, message = generate_avatar_video(
                audio_path=voice_path,
                api_key=os.getenv('HEYGEN_API_KEY'),
                avatar_id=os.getenv('HEYGEN_AVATAR_ID'),
                text=script,
                heygen_voice_id=os.getenv('HEYGEN_VOICE_ID')
            )

            # Send video
            with open(video_path, 'rb') as video_file:
                await query.message.reply_video(
                    video=video_file,
                    caption="🎬 Your AI-generated video",
                    supports_streaming=True
                )

            # Cleanup
            os.remove(voice_path)
            os.remove(video_path)

            # Clear user data
            context.user_data.clear()

        except Exception as e:
            logger.error(f"Video generation error: {e}")
            await query.edit_message_text(f"⚠️ Video generation failed: {e}")

    def setup_handlers(self, app):
        """Set up all bot handlers"""
        app.add_handler(CommandHandler('start', self.start))

        # Input type selection
        app.add_handler(CallbackQueryHandler(
            self.handle_input_type,
            pattern='^(text_input|video_idea|voice_idea)$'
        ))

        # Voice provider selection
        app.add_handler(CallbackQueryHandler(
            self.handle_voice_provider,
            pattern='^(eleven_labs|deep_labs)$'
        ))

        # Video generation decision
        app.add_handler(CallbackQueryHandler(
            self.handle_video_generation,
            pattern='^(generate_video|cancel)$'
        ))

        # Text and voice message handlers
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_content))
        app.add_handler(MessageHandler(filters.VOICE, self.process_content))

def main():
    """Main bot initialization"""
    app = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    bot = VideoCreatorBot()
    bot.setup_handlers(app)

    logger.info("Video Creator Bot started...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
