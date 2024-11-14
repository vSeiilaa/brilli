import os
from dotenv import load_dotenv

load_dotenv()

GENAI_API_KEY = os.getenv('API_KEY')
OPENAI_API_KEY = os.getenv('OPEN_AI_KEY')
DELIMITER = "####"
