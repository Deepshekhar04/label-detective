# Label Detective 🔍

AI-powered food ingredient analyzer that helps users identify potential allergens, dietary conflicts, and sustainability concerns in their food products.

## Features

- **Smart Ingredient Recognition**: OCR-powered text extraction from product labels using Google Vision API
- **Personalized Health Analysis**: Customizable profiles for allergies, dietary preferences, and sustainability goals
- **Evidence-Based Results**: Web-grounded information with credible source citations
- **Interactive Web Interface**: Beautiful, modern UI with real-time scanning
- **Scan History**: Track and review past ingredient analyses
- **Multi-Agent Architecture**: Specialized AI agents for extraction, normalization, lookup, matching, and explanation

## Quick Start

### Prerequisites

- Python 3.9+
- Google Cloud Platform account
- Required API keys:
  - Google Cloud Vision API
  - Google Gemini API
  - Google Custom Search API
  - Firestore database

### 1. Installation

```bash
# Clone and setup environment
git clone <repository-url>
cd label-detective
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=development
PORT=5000

# Google Cloud Configuration
FIRESTORE_PROJECT_ID=your-project-id
FIRESTORE_DATABASE_ID=firestoredb
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json

# API Keys
GENAI_API_KEY=your-gemini-api-key
GOOGLE_CSE_ID=your-custom-search-engine-id
GOOGLE_CSE_API_KEY=your-custom-search-api-key

# Optional Configuration
SESSION_TTL_DAYS=30
MAX_PARALLEL_LOOKUPS=6
```

### 3. Verification & Running

```bash
# Run unit tests to verify setup
pytest tests/test_tools.py -v

# Start the application
python app.py
```

Visit `http://localhost:5000` in your browser.

## Project Structure

```text
label-detective/
├── app.py                      # Flask application entry point
├── orchestrator/
│   ├── orchestrator.py         # Main orchestration logic
│   ├── tools.py                # Tool functions for agents
│   └── agents/                 # Specialized AI agents
│       ├── extractor.py        # Text extraction from images
│       ├── normalizer.py       # Ingredient name normalization
│       ├── lookup.py           # Ingredient information retrieval
│       ├── matcher.py          # Profile matching logic
│       ├── explain.py          # Result explanation
│       └── evaluator.py        # Quality assessment
├── utils/
│   ├── firestore_client.py     # Firestore database operations
│   └── logging_utils.py        # Structured logging utilities
├── static/                     # Frontend assets
├── templates/                  # Jinja2 HTML templates
├── data/                       # Local ingredient database
└── tests/                      # Unit tests
```

## Architecture

### Multi-Agent System

The application uses specialized agents that work together:

- **Extractor Agent**: Extracts ingredient text from images using OCR
- **Normalizer Agent**: Maps raw ingredient names to canonical forms
- **Lookup Agent**: Retrieves ingredient facts with parallel execution
- **Matcher Agent**: Compares ingredients against user profile
- **Explain Agent**: Generates user-friendly explanations
- **Evaluator Agent**: Assesses output quality using LLM-based judgment

### Technology Stack

- **Backend**: Flask (Python)
- **Database**: Google Firestore
- **AI/ML**: Google Gemini, Google Vision API
- **Frontend**: HTML, CSS, JavaScript
- **Monitoring**: Prometheus metrics

## Usage

### Scanning Ingredients

- **Text Input**: Paste ingredient list directly
- **Image Upload**: Upload a photo of the ingredient label

### Managing Profile

Configure your personal health and ethical preferences to get tailored analysis:

- **Allergies**: Define specific allergens with severity levels (e.g., *Peanut (High)*, *Milk (Moderate)*).
- **Dietary Requirements**: Select from standard diets like *Vegan*, *Vegetarian*, *Gluten-Free*, etc.
- **Sustainability Goals**: Set preferences for ethical consumption, such as *Avoid Palm Oil*.
- **Ingredient Blocklist**: Custom list of specific ingredients you wish to avoid (e.g., *MSG*, *Artificial Colors*).
- **Explanation Detail**: Choose your preferred depth of analysis (*Brief*, *Detailed*, or *Citations Only*).

### Understanding Results

Results include:

- **Verdict**: Safe, Caution, or Avoid
- **Conflicts**: Detailed list of problematic ingredients
- **Evidence**: Source citations for claims
- **Alternatives**: Suggested alternative products
- **Ingredient Table**: Complete breakdown with tags

## Key Endpoints

- **Scan**: `POST /scan` - Submit ingredient text or image for analysis.
- **Profile**: `GET /profile` - Manage user preferences and allergies.
- **History**: `GET /history` - View past scan results.
- **Metrics**: `GET /metrics` - Prometheus application metrics.
- **Internal**: `/api/*` routes for history saving and blocklist management.

## License & Support

This project is licensed under the MIT License. For issues or questions, please open an issue on GitHub.

---

## Built with ❤️ using Google Cloud AI
