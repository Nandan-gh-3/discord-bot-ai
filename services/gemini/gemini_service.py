# services/gemeni/gemini_service.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging

load_dotenv()
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')  # Using get to avoid KeyError
genai.configure(api_key=GEMINI_API_KEY)

# Set up the model
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 1999,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
]

model = genai.GenerativeModel(model_name="gemini-pro",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

def generate_gemini_response(prompt):
    # prompt = prompt + "\n answer in 2-3 sentences"
    try:
        logging.info("\033[38;5;191mPrompt: \n"  + prompt + "\033[0m\n")  # Green color for prompt
        response = model.generate_content(prompt)
        logging.info("\033[38;5;99mGemini: \n" + response.text + "\033[0m\n")  # Blue color for Gemini response
        return response.text
    except Exception as e:
        logging.error(e)
        return f"*ignores*"