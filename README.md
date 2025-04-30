# AI Document Question Answering System

A Django-based REST API that uses Google's Gemini AI to answer questions about uploaded documents. The system processes documents, finds relevant sections, and generates accurate responses based on the document content.

## Features

- Document upload and management (supports TXT and PDF files)
- AI-powered question answering using Google's Gemini API
- Smart text processing with TF-IDF and keyword-based relevance matching
- RESTful API with comprehensive documentation
- Docker-based deployment
- Comprehensive test suite

## Prerequisites

- Docker and Docker Compose
- Google Gemini API key
- Python 3.11+ (if running locally)

## Environment Variables

Create a `.env` file in the project root with:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Installation & Setup

1. Clone the repository:
```bash
git clone oscargil/ai-docs-prompt
cd ai_docs_prompt
```

2. Build and start the containers:
```bash
docker compose up --build
```

The application will be available at `http://localhost:8000`

## API Endpoints

### 1. Document Management
- `POST /api/documents/`: Upload a new document
  ```json
  {
    "title": "Document Title",
    "file": <file>
  }
  ```

- `GET /api/documents/`: List all documents
- `GET /api/documents/{id}/`: Retrieve a specific document
- `DELETE /api/documents/{id}/`: Delete a document

### 2. Question Answering
- `POST /api/documents/generate_response/`: Generate an AI response
  ```json
  {
    "document_id": 1,
    "question": "Your question about the document"
  }
  ```

## Testing

Run the test suite using:
```bash
docker compose run test
```

The test suite covers:
- Document upload and management
- Text processing and relevance finding
- API endpoint functionality
- Error handling

## Technical Details

### Text Processing
- Documents are split into paragraphs for processing
- Relevant sections are found using:
  - TF-IDF vectorization
  - Keyword matching
  - Context preservation
- Smart paragraph selection ensures complete context is maintained

### AI Integration
- Uses Google's Gemini 1.5 Pro model
- Implements retry logic for rate limits
- Provides context-aware responses

### Database
- PostgreSQL for document storage
- Efficient document content indexing

## Project Structure

```
.
├── documents/
│   ├── models.py      # Document model
│   ├── views.py       # API views and AI logic
│   ├── serializers.py # REST framework serializers
│   └── tests.py       # Test suite
├── docker-compose.yml # Docker configuration
├── Dockerfile        # Container definition
└── requirements.txt  # Python dependencies
```

## Dependencies

- Django 5.0.2
- Django REST Framework 3.14.0
- Google Generative AI 0.8.5
- Python-dotenv 1.0.1
- Pillow 10.2.0
- psycopg2-binary 2.9.9
- drf-spectacular 0.27.1
- PyPDF2 3.0.1

## Error Handling

The API implements comprehensive error handling for:
- Invalid document formats
- Missing or invalid parameters
- AI service rate limits
- Database connection issues

## API Documentation

Access the interactive API documentation at:
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

## Development

1. Start the development server:
```bash
docker compose up
```

2. Run tests:
```bash
docker compose run test
```

3. View logs:
```bash
docker compose logs -f
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Acknowledgments

This project was made possible thanks to:

- [Google's Gemini AI](https://ai.google.dev/) for providing the powerful language model
- [Django](https://www.djangoproject.com/) and [Django REST Framework](https://www.django-rest-framework.org/) for the robust web framework
- [scikit-learn](https://scikit-learn.org/) for the TF-IDF implementation
- [Docker](https://www.docker.com/) for containerization
- [PostgreSQL](https://www.postgresql.org/) for the reliable database
- [PyPDF2](https://pypi.org/project/PyPDF2/) for PDF processing
- [drf-spectacular](https://drf-spectacular.readthedocs.io/) for API documentation
