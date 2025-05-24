# AI Document Question Answering System

A Django-based REST API that uses Google's Gemini AI and a Retrieval Augmented Generation (RAG) pipeline with ChromaDB to answer questions about uploaded documents. The system processes documents, stores them as vector embeddings, retrieves relevant context, and generates accurate responses.

## Features

- Document upload and management (supports TXT and PDF files)
- AI-powered question answering using Google's Gemini API and ChromaDB
- Retrieval Augmented Generation (RAG) for contextually relevant answers
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
GEMINI_API_KEY="your_gemini_api_key_here"
CHROMA_DB_PATH="./chroma_db_store" 
# This is the path where the persistent ChromaDB vector store will be created.
# Default is ./chroma_db_store as defined in documents/vector_store.py.
```
Ensure `GEMINI_API_KEY` is set, as it's crucial for embedding generation and AI responses.

## Installation & Setup

1. Clone the repository:
```bash
git clone https://github.com/oscargil/ai-docs-prompt.git # Assuming this is the repo URL
cd ai-docs-prompt 
```

2. Ensure all dependencies, including `chromadb` and `google-generativeai`, are listed in `requirements.txt`. If running locally or building a new image, you might need to install/update dependencies:
```bash
pip install -r requirements.txt 
```

3. Build and start the containers:
```bash
docker compose up --build
```

The application will be available at `http://localhost:8000`

## Architecture Overview (RAG Pipeline)

The application now uses a Retrieval Augmented Generation (RAG) pipeline:

1.  **Document Upload:** Users upload text or PDF documents via the API.
2.  **Text Extraction & Chunking:** Text is extracted from the uploaded file. This text is then split into smaller, manageable paragraphs (chunks).
3.  **Embedding Generation:** These text chunks are converted into vector embeddings using Google's Generative AI embedding models (e.g., `models/text-embedding-004`).
4.  **Vector Storage:** The generated embeddings and their corresponding text chunks are stored in a ChromaDB persistent database. The path to this database is configured via the `CHROMA_DB_PATH` environment variable.
5.  **Querying:** When a user submits a question for a specific document:
    *   The question text is embedded using the same Google Generative AI embedding model, but with a `task_type` optimized for retrieval queries (e.g., "retrieval_query").
6.  **Context Retrieval:** ChromaDB is queried using the question embedding. It searches within the specified document's chunks to find the most semantically similar text chunks to the question.
7.  **Prompt Augmentation:** The retrieved text chunks (relevant context) are then inserted into a prompt that is sent to Google's Gemini generative model.
8.  **AI Response:** The Gemini model generates a response based on the augmented prompt, which includes both the original question and the relevant context retrieved from the document.

## API Endpoints

### 1. Document Management
- `POST /api/documents/`: Upload a new document
  ```json
  {
    "title": "Document Title",
    "file": "<file>"
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
docker compose run --rm test
```
(Added `--rm` to remove container after test run)

The test suite covers:
- Document upload and management
- Embedding generation (mocked)
- API endpoint functionality
- Error handling
- Vector store interactions (mocked)

## Project Structure

```
.
├── documents/
│   ├── models.py        # Document model
│   ├── views.py         # API views, RAG logic
│   ├── serializers.py   # REST framework serializers
│   ├── vector_store.py  # ChromaDB and embedding logic
│   ├── tests.py         # Integration/API tests
│   └── tests_vector_store.py # Unit tests for vector_store.py
├── docker-compose.yml   # Docker configuration
├── Dockerfile          # Container definition
└── requirements.txt    # Python dependencies
```

## Dependencies

Key dependencies include:
- Django 5.0.2
- Django REST Framework 3.14.0
- Google Generative AI (google-generativeai) 0.8.5 (for embeddings and LLM)
- ChromaDB (chromadb) ~=0.4.24 (for vector storage and retrieval)
- Python-dotenv 1.0.1
- Pillow 10.2.0
- psycopg2-binary 2.9.9
- drf-spectacular 0.27.1
- PyPDF2 3.0.1

## Error Handling

The API implements comprehensive error handling for:
- Invalid document formats
- Missing or invalid parameters
- AI service rate limits and errors
- Vector database connection issues
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
docker compose run --rm test
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

- [Google's Generative AI](https://ai.google.dev/) for providing the embedding and language models
- [ChromaDB](https://www.trychroma.com/) for the efficient vector store solution
- [Django](https://www.djangoproject.com/) and [Django REST Framework](https://www.django-rest-framework.org/) for the robust web framework
- [Docker](https://www.docker.com/) for containerization
- [PostgreSQL](https://www.postgresql.org/) for the reliable database
- [PyPDF2](https://pypi.org/project/PyPDF2/) for PDF processing
- [drf-spectacular](https://drf-spectacular.readthedocs.io/) for API documentation
```
