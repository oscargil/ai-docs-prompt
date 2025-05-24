import chromadb
import google.generativeai as genai
import os

# Configure Gemini API key
# Make sure you have GEMINI_API_KEY in your environment variables
# genai.configure(api_key=os.environ.get("GEMINI_API_KEY")) # This will be handled in settings.py or views.py where it's used

# Define the path for the persistent ChromaDB database
CHROMA_DB_PATH = "./chroma_db_store" 
COLLECTION_NAME = "document_embeddings"

# Embedding model to use
EMBEDDING_MODEL = "models/text-embedding-004" # A common choice for new embeddings

def get_chroma_client():
    """Initializes and returns a persistent ChromaDB client."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client

def get_embedding_function(): # This outer function might be less relevant if we always call embed_texts directly
    """
    Returns an embedding function using the configured Google Generative AI model.
    This function can be passed to ChromaDB during collection creation or querying if needed.
    Now includes task_type flexibility.
    """
    
    def embed_texts(texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
        """
        Generates embeddings for a list of texts using the specified task type.
        Supported task_types: "retrieval_document", "retrieval_query", "semantic_similarity", etc.
        """
        if not texts:
            return []
        
        # Ensure the genai client is configured.
        # This check might be better placed right before the genai.embed_content call
        # or handled globally.
        # if not genai.get_model(EMBEDDING_MODEL): # This check might not be robust enough
        #     raise Exception("Gemini API key not configured or model not found. Call genai.configure() first.")

        if not EMBEDDING_MODEL.startswith("models/text-embedding-") and \
           not EMBEDDING_MODEL.startswith("models/embedding-") and \
           not EMBEDDING_MODEL.startswith("models/gemini-embedding-"): # Updated check for gemini embeddings
            raise ValueError(f"Model {EMBEDDING_MODEL} is not a recognized embedding model.")

        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=texts, # Pass the list of texts directly
                task_type=task_type
            )
            return result['embedding']
        except Exception as e:
            # Log or handle the exception appropriately
            print(f"Error during embedding generation with task_type '{task_type}': {e}")
            # Depending on requirements, re-raise or return empty/None
            raise  # Re-raise the exception to make the caller aware

    return embed_texts

def generate_embeddings(texts: list[str], task_type: str = "retrieval_document", model_name: str = EMBEDDING_MODEL) -> list[list[float]]:
    """
    Generates embeddings for a list of texts using the specified task type and model.
    """
    if not texts:
        return []

    # It's assumed genai is configured before this function is called.
    # (e.g., in settings.py, apps.py, or at the start of the calling view method)

    if not model_name.startswith("models/text-embedding-") and \
       not model_name.startswith("models/embedding-") and \
       not model_name.startswith("models/gemini-embedding-"): # Updated check
        raise ValueError(f"Model {model_name} is not a recognized embedding model.")

    try:
        result = genai.embed_content(
            model=model_name,
            content=texts,
            task_type=task_type
        )
        # The structure of 'result' for batch embeddings is typically {'embedding': [[...], [...]]}
        # For single content, it's also {'embedding': [...]}
        # Ensure this matches the actual API response structure from genai library
        if 'embedding' not in result:
            raise ValueError("Embedding not found in genai response.")
        return result['embedding']
    except Exception as e:
        print(f"Error during embedding generation (task: {task_type}, model: {model_name}): {e}")
        raise

def get_or_create_collection(client=None):
    """
    Gets or creates the ChromaDB collection.
    """
    if client is None:
        client = get_chroma_client()
    
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )
    return collection

# Example of how to get the collection:
# chroma_client = get_chroma_client()
# document_collection = get_or_create_collection(client=chroma_client)
# print(f"Successfully connected to ChromaDB and got collection: {document_collection.name}")
