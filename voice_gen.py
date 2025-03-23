import requests
import logging

logger = logging.getLogger(__name__)

HEYGEN_BASE_URL = "https://api.heygen.com"

def generate_voice(text: str, eleven_api_key: str, heygen_api_key: str) -> str:
    """Generate voiceover and return Heygen audio asset ID (verified)"""
    VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
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

        # 2. Upload to Heygen using CORRECT ENDPOINT
        upload_response = requests.post(
            f"https://upload.heygen.com/v1/asset",
            headers={"X-Api-Key": heygen_api_key},
            files={"file": ("audio.mp3", audio_data, "audio/mpeg")},
            timeout=100
        )
        
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