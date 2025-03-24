import requests
import logging

logger = logging.getLogger(__name__)

HEYGEN_BASE_URL = "https://api.heygen.com"

def generate_voice(text: str, eleven_api_key: str, heygen_api_key: str) -> str:
    """Generate voiceover and return Heygen audio asset ID (verified)"""
    VOICE_ID = "d0grukerEzs069eKIauC"
    MODEL_ID = "eleven_monolingual_v1"
    
    try:
        # 1. Generate audio with ElevenLabs
        headers = {
            "xi-api-key": eleven_api_key,
            "Content-Type": "application/json",
            "accept": "audio/mpeg"
        }
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers=headers,
            json={
                "text": text,
                "model_id": MODEL_ID,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "speed": 0.7
                }
            },
            timeout=100
        )
        response.raise_for_status()
        audio_data = response.content
        
        # Save the audio data to a local file (audio.mp3)
        local_audio_path = "audio.mp3"
        with open(local_audio_path, "wb") as f:
            f.write(audio_data)

        url = "https://upload.heygen.com/v1/asset"
        header = {
            "Content-Type": "audio/mpeg",
            "X-Api-Key": heygen_api_key
        }

        file_path = "C:\\learnings\\tele-bot\\audio.mp3"

        
        with open(file_path, "rb") as file:
            upload_response = requests.post(url, headers=header, data=file)

        
        # Handle non-JSON responses
        try:
            upload_response.raise_for_status()
            response_data = upload_response.json()
        except requests.exceptions.JSONDecodeError:
            logger.error(f"Invalid response: {upload_response.text}")
            raise Exception("Heygen API returned non-JSON response")
        
        # Verify response structure
        if not response_data.get("data", {}).get("asset_id"):
            raise Exception("Missing asset ID in Heygen response")
        
        return response_data["data"]["asset_id"]

    except requests.exceptions.RequestException as e:
        error_msg = f"API Error: {str(e)}"
        if hasattr(e, "response") and e.response:
            error_msg += f" | Response: {e.response.text}"
        logger.error(error_msg)
        raise Exception("Voice processing failed")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise
