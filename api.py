import os
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from extractor import SUPPORTED_IMAGE_TYPES, extract_text_from_file
from llm_client import extract_catalog_from_text
from parser import parse_and_validate_json

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB upload limit
CORS(app)

@app.route('/extract-catalog', methods=['POST'])
def extract_catalog():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    extension = Path(file.filename or "").suffix.lower()
    if extension != ".pdf" and extension not in SUPPORTED_IMAGE_TYPES:
        return jsonify({"error": "Upload a PDF or supported image file"}), 400

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            temp_path = temp_file.name
        file.save(temp_path)
        raw_text = extract_text_from_file(temp_path)
        llm_raw_output = extract_catalog_from_text(raw_text)
        clean_catalog = parse_and_validate_json(llm_raw_output)
        return jsonify(clean_catalog), 200
        
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 422
    except Exception as e:
        return jsonify({"error": f"Server processing error: {str(e)}"}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(port=port, debug=True)