import os
from typing import Dict, Optional
import json

def load_system_prompt(prompt_filename: str ="", lang: str = 'zh') -> str:
    """
    Load system prompt from files based on specified text file name and language
    
    Args:
        prompt_filename: The prompt file name
        lang: Language code ('en' or 'zh'), defaults to 'zh'
        
    Returns:
        Combined prompt string
        
    Raises:
        FileNotFoundError: If prompt files are not found
        Exception: For other loading errors
    """
    try:
        # Get base directory for prompts
        current_file = os.path.abspath(__file__)
        base_dir = os.path.join(os.path.dirname(current_file), '..', 'prompts')
        
        # Validate and normalize language code
        lang = lang.lower()
        if lang not in ['en', 'zh']:
            lang = 'en'
            
        # Construct language-specific directory path
        lang_dir = os.path.join(base_dir, lang)
        
        # Load base prompt
        promptfile = os.path.join(lang_dir, prompt_filename)
        if not os.path.exists(promptfile):
            print(f"Prompt file does not exist at: {promptfile}")
            raise FileNotFoundError(f"Base prompt file not found at {promptfile}")

        with open(promptfile, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
            return prompt

    except Exception as e:
        print(f"Error loading prompt: {str(e)}")
        raise Exception(f"Failed to load prompt: {str(e)}")

def load_json_prompt(prompt_filename: str = "", lang: str = 'zh') -> dict:
    """
    Load JSON prompt from files based on specified JSON file name and language
    
    Args:
        prompt_filename: The JSON prompt file name
        lang: Language code ('en' or 'zh'), defaults to 'zh'
        
    Returns:
        dict: Parsed JSON content
        
    Raises:
        FileNotFoundError: If JSON prompt files are not found
        JSONDecodeError: If JSON parsing fails
        Exception: For other loading errors
    """
    try:
        # Get base directory for prompts
        current_file = os.path.abspath(__file__)
        base_dir = os.path.join(os.path.dirname(current_file), '..', 'prompts')
        
        # Validate and normalize language code
        lang = lang.lower()
        if lang not in ['en', 'zh']:
            lang = 'en'
            
        # Construct language-specific directory path
        lang_dir = os.path.join(base_dir, lang)
        
        # Load JSON prompt
        promptfile = os.path.join(lang_dir, prompt_filename)
        if not os.path.exists(promptfile):
            print(f"JSON prompt file does not exist at: {promptfile}")
            raise FileNotFoundError(f"JSON prompt file not found at {promptfile}")

        with open(promptfile, 'r', encoding='utf-8') as f:
            return json.load(f)

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
        raise
    except Exception as e:
        print(f"Error loading JSON prompt: {str(e)}")
        raise Exception(f"Failed to load JSON prompt: {str(e)}")