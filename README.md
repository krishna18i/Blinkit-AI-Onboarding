# 📦 Universal AI Vendor Catalog Sync

A clean, intelligent assistant designed to automate how businesses handle vendor rate lists. Whether a supplier sends a clean digital PDF or a quick, handwritten photo taken on a smartphone, this platform reads the document, standardizes the catalog data, and calculates profit margins automatically.

---

### 🌟 Key Capabilities

• 📄 **Multi-Format Reading**

Processes digital PDFs and camera photos seamlessly. Includes built-in image compression to resize high-resolution photos, dropping scan times from minutes down to seconds.

• 🧠 **Resilient AI Extraction**

Uses fast natural language models to extract item details and prices. Built with text chunking and background retry logic to handle large documents reliably without crashing.

• 🎯 **Smart Product Matching**

Compares messy vendor item names against your company's official Master SKU database. Automatically maps recognized products and safely flags unknown items as new SKUs.

• 📈 **Dynamic Profit Engine**

Acts as a real-time financial helper. Applies company target margin rules to calculate wholesale cost, recommended selling prices, and projected profit, using visual indicators (🟢, 🟡, 🔴) to highlight margin health.

• ✏️ **Interactive Operator Dashboard**

Provides an Excel-like table where team members can double-check AI outputs, adjust pricing, resolve typos, and export clean CSV or JSON files with one click.

---

### 🛠️ Tech Stack & Tools

• **Frontend & Operations UI:** Streamlit (Interactive Web Dashboard & Editable Tables)

• **File Ingestion:** EasyOCR (Multilingual Image Processing) & PDFPlumber (Digital PDF Extraction)

• **AI & Processing Engine:** Groq API (Llama 3.1 8B for JSON Parsing) & RapidFuzz (String Matching)

• **Resilience & Validation:** Pydantic (Data Schema Enforcement) & Tenacity (Automated Retry Logic)

---

### 🔄 Step-by-Step Workflow

1. 📥 **Upload:** Upload a vendor menu or rate list (PDF or Image) and optionally attach your company's Master Catalog CSV.
2. 🔍 **Scan & Extract:** The engine optimizes the file, runs OCR text extraction, and uses AI to pull out item names and quoted rates.
3. ⚙️ **Match & Price:** Extracted items are matched against your master catalog while the system calculates cost prices, selling prices, and profit margins.
4. 📊 **Review & Export:** Review the populated dashboard, make any manual tweaks directly in the table, and download the standardized data file.

---

### 🚀 Getting Started

1. **Install Dependencies:**
```bash
pip install -r requirements.txt

```


2. **Configure API Keys:**
Create a `.env` file in the root folder and add your Groq API key:
```env
GROQ_API_KEY=your_api_key_here

```


3. **Launch the Dashboard:**
```bash
streamlit run streamlit_app.py

```



---

### 🔮 Future Roadmap

• 🗺️ **Semantic Vector Search:** Upgrading string matching to vector embeddings to support cross-lingual catalog matching (such as Hindi item names to English master SKUs).

• ⚡ **Enterprise API Service:** Wrapping the ingestion engine into FastAPI REST endpoints for direct integration into enterprise ERP systems.