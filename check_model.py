import os
from dotenv import load_dotenv
load_dotenv()

from groq import Groq


client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# This asks Groq directly: "What models am I allowed to use?"
models = client.models.list()
print("Models available to your API key:")
for m in models.data:
    print("-", m.id)