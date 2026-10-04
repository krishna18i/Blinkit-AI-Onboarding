# Blinkit AI Vendor Onboarding Pipeline 🚀

An end-to-end automated catalog extraction tool designed for quick-commerce operations. It converts unstructured vendor PDFs (price lists, menus, and product sheets) into clean, database-ready JSON schemas in seconds.

## 🛠️️ Tech Stack
- **Backend:** Python, Flask, Flask-CORS, pdfplumber, json-repair, Groq API (`qwen/qwen3.8-27b`)
- **Frontend:** Chrome Extension (Manifest V3, Side Panel API, JavaScript, HTML5, CSS3)

## 📐 Architecture & Workflow
1. **Frontend Ingestion:** Sales or vendor operations teams upload a PDF via a custom Chrome Extension side-panel.
2. **Middleware API:** A local Flask server receives the file via a `POST` request, extracts the raw text using `pdfplumber`, and routes it to the Groq LLM API.
3. **Resilient Parsing:** The backend uses Regex isolation and automated syntax repair (`json-repair`) to handle non-deterministic LLM outputs, ensuring 100% schema compliance.
4. **Dynamic UI:** The extension parses the resulting JSON and dynamically renders products with category badges and Indian Rupee (`₹`) formatting.

## ⚙️ How to Run Locally

### 1. Run the Python Backend
\`\`\`bash
pip install flask flask-cors pdfplumber groq json-repair
python catalog_engine.py
\`\`\`

### 2. Load the Chrome Extension
1. Open Google Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** in the top right.
3. Click **Load unpacked** and select the `Blinkit_Extension` folder.
4. Open the extension side-panel in your browser, upload a sample vendor PDF, and extract!