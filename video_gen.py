import requests
import time
import logging
import os
import json

logger = logging.getLogger(__name__)

HEYGEN_BASE_URL = "https://api.heygen.com"

def generate_avatar_video(script: str, api_key: str, avatar_id: str, voice_id: str = "en-US-male-1") -> str:
    """Generate video directly from script text"""
    try:
        api_key = "OGRiM2FiZmFmNmRmNGQzN2FkYmFmMzIxZTFjNzQxOGQtMTc0MjcyODM3OQ=="
        # Create request payload
        payload ={
                    "video_inputs": [
                        {
                            "character": {
                                "type": "avatar",
                                "avatar_id": avatar_id,
                                "avatar_style": "normal"
                            },
                            "voice": {
                                "type": "text",
                                "input_text": script,
                                "voice_id": voice_id
                            },
                            "background": {
                                "type": "color",
                                "value": "#008000"
                            }
                        }
                    ],
                    "dimension": {
                        "width": 1280,
                        "height": 720
                    }
                }
        
        # Log the request payload for debugging
        logger.info(f"Sending request to HeyGen API with payload: {json.dumps(payload)}")
        
        # Create video request
        api_url = f"{HEYGEN_BASE_URL}/v2/video/generate"
        header = {"X-Api-Key": api_key, "Content-Type": "application/json"}
        print("api_url", api_url)
        print("header", header)
        print("payload", payload)
        response = requests.post(api_url,
            headers=header,
            json=payload
        )
        
        # Log the full response for debugging
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
        response.raise_for_status()
        
        response_data = response.json()
        video_id = response_data.get("data", {}).get("video_id")
        
        if not video_id:
            raise Exception(f"No video_id in response: {response_data}")
            
        logger.info(f"Video creation started. ID: {video_id}")

        # Monitor status
        while True:
            status_response = requests.get(
                f"{HEYGEN_BASE_URL}/v1/video_status.get",  # Note: using v1 endpoint
                headers={"X-Api-Key": api_key},
                params={"video_id": video_id}
            )
            status_data = status_response.json()
            
            logger.info(f"Status check response: {status_data}")
            
            current_status = status_data.get("data", {}).get("status")
            if current_status == "completed":
                video_url = status_data.get("data", {}).get("video_url")
                break
            elif current_status in ("failed", "canceled"):
                error_msg = status_data.get("data", {}).get("error", "Unknown error")
                raise Exception(f"Generation failed: {error_msg}")
            
            logger.info(f"Current status: {current_status} - polling in 5s...")
            time.sleep(5)

        # Download video
        video_path = f"output_{video_id}.mp4"
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(video_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return video_path

    except requests.exceptions.RequestException as e:
        logger.error(f"Heygen API Error: {str(e)}")
        try:
            if hasattr(e, 'response') and e.response:
                error_content = e.response.text
                logger.error(f"Error response content: {error_content}")
                
                try:
                    error_json = json.loads(error_content)
                    error_detail = error_json.get('error', {}).get('message', 'No detailed error message')
                    logger.error(f"Parsed error detail: {error_detail}")
                    raise Exception(f"Video creation failed: {error_detail}")
                except json.JSONDecodeError:
                    raise Exception(f"Video creation failed with non-JSON response: {error_content}")
            else:
                raise Exception(f"Video creation failed: {str(e)}")
        except Exception as inner_e:
            logger.error(f"Error while handling API error: {str(inner_e)}")
            raise Exception(f"Video creation failed: {str(e)}")