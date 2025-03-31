import os
import logging
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_script(user_input: str, input_type: str) -> str:
    """
    Generate a refined script based on user input and input type
    
    :param user_input: Original text from user
    :param input_type: Type of input (text_script, video_idea, voice_idea)
    :return: Refined and optimized script
    """
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        input_type_prompts = {
            'text_script': "Refine this script for clarity and engagement:",
            'video_idea': "Convert this video idea into a compelling script:",
            'voice_idea': "Transform this voice idea into a structured script:",
            'voice_script': "Polish this voice script for better delivery:"
        }
        
        system_prompt = """
        You are a professional script writer. Generate clear, concise, and engaging scripts
        that are suitable for video narration. Focus on:
        - Clarity of message
        - Conversational tone
        - Appropriate length (1-2 paragraphs)
        - Engaging narrative structure
        MOST IMPORTANTLY: Generate the script in the same language and style as the input.
                          In case of Hindi language output text is not coming as expected, please try again.
                          You have to make it readable, its not. You need to format is very well. 
                          And make sure the output format of the text is suitable for converting it to voice.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{input_type_prompts.get(input_type, '')} {user_input}"}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        generated_script = response.choices[0].message.content.strip()
        
        # Basic validation
        if len(generated_script) < 50:
            raise ValueError("Generated script is too short")
        
        logger.info(f"Script generated successfully for input type: {input_type}")
        return generated_script
    
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        raise ValueError(f"Could not generate script: {e}")
