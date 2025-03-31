import os
import time
import logging
import requests
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_asset_to_heygen(file_path: str, api_key: str, content_type: str = "audio/x-wav") -> str:
    """
    Upload an asset to HeyGen with robust error handling
    
    :param file_path: Path to the file to upload
    :param api_key: HeyGen API key
    :param content_type: MIME content type of the file
    :return: Asset ID or None if upload fails
    """
    try:
        # Validate file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if os.path.getsize(file_path) == 0:
            raise ValueError("File is empty")
        
        # Upload endpoint
        url = "https://upload.heygen.com/v1/asset"
        
        # Prepare headers
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": content_type
        }

        print("Headers: ", headers)
        print("URL: ", url)
        print("File Path: ", file_path)
        
        # Open and upload file
        with open(file_path, 'rb') as f:
            response = requests.post(
                url, 
                data=f, 
                headers=headers, 
                timeout=30
            )
        
        # Check response
        response.raise_for_status()
        
        # Extract asset ID
        result = response.json()
        asset_id = result.get("data", {}).get("id")
        
        if not asset_id:
            raise ValueError("No asset ID received from HeyGen")
        
        logger.info(f"Successfully uploaded asset: {asset_id}")
        return asset_id
    
    except Exception as e:
        logger.error(f"Asset upload error: {e}")
        raise ValueError(f"Asset upload failed: {e}")

def generate_avatar_video(
    audio_path: str = None, 
    api_key: str = None, 
    avatar_id: str = None, 
    text: str = None, 
    heygen_voice_id: str = None
) -> tuple:
    """
    Generate avatar video with comprehensive fallback mechanism
    
    :param audio_path: Path to audio file
    :param api_key: HeyGen API key
    :param avatar_id: HeyGen avatar ID
    :param text: Fallback text for voice generation
    :param heygen_voice_id: HeyGen voice ID for text-to-speech
    :return: Tuple of (video_path, message)
    """
    try:
        # Validate inputs
        if not api_key or not avatar_id:
            raise ValueError("Missing HeyGen API key or Avatar ID")
        
        # Try to upload audio if provided
        audio_asset_id = None
        if audio_path and os.path.exists(audio_path):
            try:
                audio_asset_id = upload_asset_to_heygen(audio_path, api_key)
            except Exception as upload_error:
                logger.warning(f"Audio upload failed: {upload_error}")
        
        # Prepare video generation payload
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # Determine video input method
        if audio_asset_id:
            # Use uploaded audio
            video_inputs = [{
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "scale": 1.0,
                    "style": "normal"
                },
                "voice": {
                    "type": "audio",
                    "audio_asset_id": audio_asset_id
                },
                "background": {
                    "type": "color",
                    "value": "#f6f6fc"
                }
            }]
        elif text and heygen_voice_id:
            # Fallback to text-to-speech
            video_inputs = [{
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "scale": 1.0,
                    "style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": text,
                    "voice_id": heygen_voice_id
                },
                "background": {
                    "type": "color",
                    "value": "#f6f6fc"
                }
            }]
        else:
            raise ValueError("No valid audio or text input for video generation")
        
        # Prepare full payload
        payload = {
            "video_inputs": video_inputs,
            "dimension": {"width": 1280, "height": 720},
            "test": False
        }
        
        # Send video generation request
        response = requests.post(
            "https://api.heygen.com/v2/video/generate",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        # Check response
        response.raise_for_status()
        response_data = response.json()
        
        # Extract video ID
        video_id = response_data.get("data", {}).get("video_id")
        if not video_id:
            raise ValueError("No video ID in response")
        
        # Poll for video status
        return poll_video_status(video_id, api_key)
    
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise

def poll_video_status(video_id: str, api_key: str, max_retries: int = 30, interval: int = 10) -> tuple:
    """
    Poll HeyGen video generation status
    
    :param video_id: Video generation job ID
    :param api_key: HeyGen API key
    :param max_retries: Maximum number of polling attempts
    :param interval: Seconds between polling attempts
    :return: Tuple of (video_path, message)
    """
    headers = {"x-api-key": api_key}
    
    for attempt in range(1, max_retries + 1):
        try:
            # Check video status
            status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
            response = requests.get(status_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse response
            data = response.json().get("data", {})
            status = data.get("status")
            
            # Handle different statuses
            if status == "completed":
                video_url = data.get("video_url")
                if not video_url:
                    raise ValueError("No video URL in completed response")
                
                # Download video
                return download_video(video_url)
            
            elif status == "failed":
                raise ValueError("Video generation failed on server")
            
            # Wait before next attempt
            logger.info(f"Video status: {status} (Attempt {attempt}/{max_retries})")
            time.sleep(interval)
        
        except Exception as e:
            logger.warning(f"Status polling error (Attempt {attempt}): {e}")
            time.sleep(interval)
    
    raise TimeoutError("Video generation timed out")

def download_video(url: str) -> tuple:
    """
    Download generated video
    
    :param url: Video download URL
    :return: Tuple of (video_path, message)
    """
    try:
        # Download video
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Generate unique filename
        video_path = f"generated_video_{uuid.uuid4().hex}.mp4"
        
        # Save video
        with open(video_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Validate download
        if os.path.getsize(video_path) == 0:
            os.remove(video_path)
            raise ValueError("Downloaded video is empty")
        
        return video_path, "Video successfully generated"
    
    except Exception as e:
        logger.error(f"Video download error: {e}")
        raise ValueError(f"Video download failed: {e}")
