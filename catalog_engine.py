from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
import pdfplumber
import json
import re
from groq import Groq
from json_repair import repair_json
import os

app = Flask(__name__)
CORS(app) 


client = Groq(api_key=os.getenv("GROQ_API_KEY")) # Paste your real key here

def process_vendor_data(raw_text):
    """Sends messy text to Groq and extracts clean JSON safely using Regex and repair."""
    
    system_prompt = """
    You are an expert catalog data extraction AI for Blinkit.
    Your job is to read messy, unstructured vendor price lists and extract the products into JSON.
    
    You MUST return ONLY a JSON object matching this structure:
    {
        "products": [
            {
                "item_name": "Product Name",
                "category": "Category",
                "mrp": 100,
                "seo_description": "Two sentence description."
            }
        ]
    }
    """

    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b", 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract products from this vendor text:\n{raw_text}"}
        ],
        temperature=0.1,
        max_tokens=4000  # Forces the model to allow a massive JSON output
    )
    
    raw_output = response.choices[0].message.content or ""
    
    # Use Regex to isolate the outer JSON block {...}
    json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
    
    if json_match:
        json_string = json_match.group(0)
        # CRITICAL FIX: Repair the JSON string before loading it
        fixed_json = repair_json(json_string)
        return json.loads(fixed_json)
    else:
        print("\n--- RAW OUTPUT FROM GROQ ---")
        print(raw_output)
        raise ValueError("The AI model did not return a valid JSON object.")

@app.route('/extract-catalog', methods=['POST'])
def extract_catalog():
    # 1. Catch the file sent by the webhook or extension
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    temp_path = "temp_vendor.pdf"
    file.save(temp_path)
    
    # 2. Extract the text
    text = ""
    with pdfplumber.open(temp_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
                
    # 3. Send to Groq and return the clean JSON
    clean_catalog = process_vendor_data(text)
    
    # 4. Clean up the temp file
    os.remove(temp_path)
    
    return jsonify(clean_catalog)

if __name__ == "__main__":
    print("Catalog Engine API running on http://127.0.0.1:5000")
    app.run(port=5000)