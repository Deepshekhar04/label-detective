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

### Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd label-detective
```

1. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

1. **Set up environment variables**

Create a `.env` file in the root directory:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here

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
PORT=5000
FLASK_ENV=development
```

1. **Run the application**

```bash
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

1. **Extractor Agent**: Extracts ingredient text from images using OCR
1. **Normalizer Agent**: Maps raw ingredient names to canonical forms
1. **Lookup Agent**: Retrieves ingredient facts with parallel execution
1. **Matcher Agent**: Compares ingredients against user profile
1. **Explain Agent**: Generates user-friendly explanations
1. **Evaluator Agent**: Assesses output quality using LLM-based judgment

### Technology Stack

- **Backend**: Flask (Python)
- **Database**: Google Firestore
- **AI/ML**: Google Gemini, Google Vision API
- **Frontend**: HTML, CSS, JavaScript
- **Monitoring**: Prometheus metrics

## Usage

### Scanning Ingredients

1. **Text Input**: Paste ingredient list directly
1. **Image Upload**: Upload a photo of the ingredient label

### Managing Profile

Configure your dietary preferences:

```python
{
  "allergies": [
    {"name": "Peanut", "severity": "high"},
    {"name": "Milk", "severity": "moderate"}
  ],
  "diet_tags": ["vegan", "gluten-free"],
  "sustainability_goals": ["avoid_palm_oil"],
  "ingredient_blocklist": ["MSG", "Artificial colors"],
  "explain_level": "detailed"  # Options: "brief", "detailed", "citations_only"
}
```

### Understanding Results

Results include:

- **Verdict**: Safe, Caution, or Avoid
- **Conflicts**: Detailed list of problematic ingredients
- **Evidence**: Source citations for claims
- **Alternatives**: Suggested alternative products
- **Ingredient Table**: Complete breakdown with tags

## Testing

Run unit tests:

```bash
pytest tests/test_tools.py -v
```

## Deployment

### Google Cloud Run

1. **Build and deploy**

```bash
gcloud run deploy label-detective \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

1. **Set environment variables** via Cloud Run console or:

```bash
gcloud run services update label-detective \
  --set-env-vars FIRESTORE_PROJECT_ID=your-project-id,GENAI_API_KEY=your-key
```

## Security & Privacy

- Session keys stored in `.env` (not committed)
- User data encrypted in Firestore
- No third-party tracking
- Credentials in `.gitignore`
- HTTPS enforced in production

## Performance

- **Parallel Execution**: Up to 6 concurrent ingredient lookups
- **Caching**: Local ingredient database for common items
- **TTL Management**: Automatic session cleanup (30-day default)
- **Monitoring**: Prometheus metrics at `/metrics`

## API Endpoints

### Public Routes

- `GET /` - Home page with scan interface
- `POST /scan` - Submit ingredient scan
- `GET /profile` - User profile management
- `GET /history` - Scan history
- `GET /metrics` - Prometheus metrics

### API Routes

- `POST /api/save_to_history` - Save scan to history
- `POST /api/block_ingredient` - Add ingredient to blocklist
- `POST /api/accept_disclaimer` - Accept disclaimer

## Monitoring

Access Prometheus metrics:

```plaintext
http://localhost:5000/metrics
```

Metrics include:

- Request counts by endpoint
- Response times
- Error rates
- Active sessions

## License

This project is licensed under the MIT License.

## Support

For issues or questions, please open an issue on GitHub.

---

## Built with ❤️ using Google Cloud AI
