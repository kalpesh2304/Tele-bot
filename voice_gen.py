import os
import uuid
import logging
import requests
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_eleven_labs_voice(text: str, api_key: str, voice_id: str) -> str:
    """Generate voice using ElevenLabs API with enhanced error handling"""
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "accept": "audio/mpeg"
        }

        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.2,
                "speaker_boost": True
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        audio_path = f"eleven_voice_{uuid.uuid4().hex}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)

        return audio_path

    except requests.RequestException as e:
        logger.error(f"ElevenLabs API error: {e}")
        raise ValueError(f"Voice generation failed: {e}")

def generate_deep_labs_voice(text: str, base_url: str, ref_audio_id: str = None) -> str:
    """Generate voice using Deep Labs API with comprehensive polling"""
    try:
        generate_url = f"https://api.msganesh.com/itts/generate_speech"
        headers = {"Content-Type": "application/json"}
        ref_audio_id = os.environ["DEEP_LABS_REF_VOICE_ID"]
        payload = {
                    "text": text,
                    "ref_audio_id": ref_audio_id
                    }
        
        if ref_audio_id:
            payload["ref_audio_id"] = ref_audio_id

        print("Payload: ", payload)
        print("Headers: ", headers)
        print("Generate URL: ", generate_url)
        response = requests.post(generate_url, json=payload, headers=headers, timeout=200)
        response.raise_for_status()

        audio_id = response.json().get("id")
        if not audio_id:
            raise ValueError("No audio ID received from Deep Labs")

        for attempt in range(10):
            try:
                download_url = f"https://api.msganesh.com/itts/{audio_id}.wav"
                audio_response = requests.get(download_url, timeout=30)
                audio_response.raise_for_status()

                audio_path = f"deep_voice_{uuid.uuid4().hex}.wav"
                with open(audio_path, "wb") as f:
                    f.write(audio_response.content)

                return audio_path

            except requests.RequestException:
                time.sleep(min(2 ** attempt, 30))

        raise TimeoutError("Could not retrieve voice audio after multiple attempts")

    except Exception as e:
        logger.error(f"Deep Labs voice generation error: {e}")
        raise ValueError(f"Voice generation failed: {e}")

def generate_voice(text: str, provider: str, **kwargs) -> str:
    """Unified voice generation method"""
    try:
        if provider == 'eleven_labs':
            return generate_eleven_labs_voice(
                text,
                api_key=kwargs.get('eleven_api_key'),
                voice_id=kwargs.get('voice_id'))
        elif provider == 'deep_labs':
            return generate_deep_labs_voice(
                text,
                base_url=kwargs.get('base_url'),
                ref_audio_id=kwargs.get('ref_audio_id')
            )
        else:
            raise ValueError(f"Unsupported voice provider: {provider}")
    except Exception as e:
        logger.error(f"Voice generation error: {e}")
        raise
