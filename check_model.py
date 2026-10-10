
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(f"API key missing. Check: {env_path}")

client = Groq(api_key=api_key)

models = client.models.list()

print("Models available to your API key:")
for model in models.data:
    print("-", model.id)
