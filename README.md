# Blinkit AI Vendor Onboarding Pipeline 🚀

An end-to-end automated catalog extraction tool designed for quick-commerce operations. It converts unstructured vendor PDFs (price lists, menus, and product sheets) into clean, database-ready JSON schemas in seconds.

## 🛠️️ Tech Stack
- **Backend:** Python, Flask, Flask-CORS, pdfplumber, EasyOCR (English/Hindi), Pydantic, json-repair, tenacity, Groq API (`llama-3.1-8b-instant` by default)
- **Frontend:** Chrome Extension (Manifest V3, Side Panel API, JavaScript, HTML5, CSS3)

## 📐 Architecture & Workflow
1. **Frontend Ingestion:** Sales or vendor operations teams upload a PDF via a custom Chrome Extension side-panel.
2. **Middleware API:** A local Flask server receives a PDF or vendor menu photo. The backend extracts selectable PDF text and uses EasyOCR on photos and scanned pages, enhancing contrast and correcting image orientation before extraction.
3. **Resilient Extraction:** Failed or empty Groq responses are retried up to three times. If Groq rejects the configured model, the backend checks the API key's available models and selects a supported fallback. Regex isolation and `json-repair` recover JSON, then Pydantic validates each chunk and applies optional-field defaults.
4. **Dynamic UI:** The extension parses the resulting JSON and dynamically renders products with category badges and Indian Rupee (`₹`) formatting.

## ⚙️ How to Run Locally

### 1. Run the Python Backend
\`\`\`bash
pip install -r requirements.txt
python catalog_engine.py
\`\`\`

Set `GROQ_API_KEY` before running the backend. The pinned `httpx` version keeps
the Groq SDK compatible with its client constructor. Override the default model with
`GROQ_MODEL` or pass a model name to `extract_catalog_from_text()`.
The first OCR run downloads EasyOCR's detection and English/Hindi recognition models.

### 2. Load the Chrome Extension
1. Open Google Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** in the top right.
3. Click **Load unpacked** and select the `Blinkit_Extension` folder.
4. Open the extension side-panel in your browser, upload a sample vendor PDF, and extract!