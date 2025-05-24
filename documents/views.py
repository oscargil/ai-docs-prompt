import os
import time
import google.generativeai as genai
from PyPDF2 import PdfReader
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from .models import Document
from .serializers import DocumentSerializer, PromptSerializer
import re
# from sklearn.feature_extraction.text import TfidfVectorizer # Removed
# from sklearn.metrics.pairwise import cosine_similarity # Removed
# import numpy as np # Removed
from .vector_store import get_chroma_client, get_or_create_collection, generate_embeddings as get_embeddings_for_texts # Updated import
# from django.conf import settings # Removed duplicate
# import google.generativeai as genai # Removed duplicate

class DocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing documents and generating AI responses.
    """
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def split_into_paragraphs(self, text):
        """Split text into paragraphs and clean them."""
        # Split by double newlines or multiple newlines
        paragraphs = re.split(r'\n\s*\n', text)
        # Clean and filter paragraphs
        cleaned_paragraphs = []
        for p in paragraphs:
            # Clean whitespace and normalize
            cleaned = ' '.join(p.strip().split())
            # Only keep paragraphs with meaningful content (more than 20 characters)
            if len(cleaned) > 20:
                cleaned_paragraphs.append(cleaned)
        return cleaned_paragraphs

    # find_relevant_paragraphs method removed.

    def perform_create(self, serializer):
        document = serializer.save()
        # Extract text content from the document file
        try:
            if document.file.name.endswith('.txt'):
                with open(document.file.path, 'r', encoding='utf-8') as file:
                    content = file.read()
            elif document.file.name.endswith('.pdf'):
                pdf_reader = PdfReader(document.file.path)
                content = ""
                for page in pdf_reader.pages:
                    extracted_page_text = page.extract_text()
                    if extracted_page_text: # Ensure text was extracted
                        content += extracted_page_text + "\n"
            else:
                # It's good to provide a message if the file type is not supported for content extraction
                # Or raise an error that can be caught and handled
                print(f"Unsupported file type for content extraction: {document.file.name}")
                # document.content remains blank or handle as an error
                # For now, let's allow document creation but content might be empty if not txt/pdf
                content = "" # Default to empty if not txt/pdf or error

            document.content = content # Save full extracted content
            document.save() # Save the document instance with extracted content

            # --- Start of ChromaDB Integration ---
            if document.content and document.content.strip(): # Proceed only if there's content
                # Ensure Gemini API is configured
                # This should ideally be done once globally (e.g., in settings.py or apps.py)
                # For now, let's ensure it's called before embedding generation
                if not settings.GEMINI_API_KEY:
                    print("GEMINI_API_KEY not found in settings.")
                    # Handle error appropriately, maybe skip embedding or raise an exception
                    return # Or raise an error

                # Check if genai is already configured to avoid re-configuring if not necessary
                # This simple check might not be foolproof for all genai library states
                # A more robust check might involve trying a lightweight API call or checking a specific attribute
                try:
                    # A lightweight way to check if a model can be retrieved, implying configuration
                    genai.get_model("models/gemini-1.5-pro-002") # Using a model known from generate_response
                except Exception: # Broad exception, refine if specific configuration error is known
                    # If get_model fails, it's likely not configured or API key is invalid
                    print("Configuring Gemini API key in perform_create.")
                    genai.configure(api_key=settings.GEMINI_API_KEY)


                paragraphs = self.split_into_paragraphs(document.content)

                if paragraphs:
                    try:
                        # Generate embeddings for the paragraphs
                        # The imported 'get_embeddings_for_texts' is the 'embed_texts' from vector_store.py
                        embeddings = get_embeddings_for_texts(paragraphs) # This calls genai.embed_content

                        # Prepare data for ChromaDB
                        ids = [f"{document.id}_chunk_{i}" for i, _ in enumerate(paragraphs)]
                        metadatas = [{
                            "document_id": str(document.id), # Store document ID as string
                            "document_title": document.title,
                            "chunk_index": i
                        } for i, _ in enumerate(paragraphs)]

                        # Get ChromaDB collection
                        chroma_client = get_chroma_client() # From vector_store.py
                        collection = get_or_create_collection(client=chroma_client) # From vector_store.py

                        # Add to ChromaDB
                        collection.add(
                            ids=ids,
                            embeddings=embeddings,
                            documents=paragraphs, # Store the actual text of the paragraph
                            metadatas=metadatas
                        )
                        print(f"Added {len(paragraphs)} chunks from document {document.id} to ChromaDB.")
                    except Exception as e:
                        # Log the error and potentially inform the user or admin
                        print(f"Error during ChromaDB ingestion for document {document.id}: {e}")
                        # Depending on policy, you might want to delete the document or mark it as not indexed
            # --- End of ChromaDB Integration ---

        except FileNotFoundError:
            print(f"Error: File not found for document ID {document.id} at path {document.file.path}")
            # Handle error, perhaps by setting document status or logging
            # For now, the document object is created but content extraction and embedding will fail/be skipped
        except ValueError as ve: # Catch specific error for unsupported file type
            print(f"ValueError during content extraction for document {document.id}: {ve}")
            # Handle as above
        except Exception as e:
            # General error handling for content extraction
            print(f"Error extracting content for document {document.id}: {e}")
            # document.content might be empty or partially filled.

    # The method should not explicitly return anything unless it's overriding a DRF default
    # that requires it. perform_create usually doesn't.

    @extend_schema(
        summary="Generate AI response",
        description="Generate an AI response using the specified document as context",
        request=PromptSerializer,
        responses={
            200: {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "example": {
                            "response": "The AI-generated response based on the document content"
                        }
                    }
                }
            },
            404: {
                "description": "Document not found",
                "content": {
                    "application/json": {
                        "example": {
                            "error": "Document not found"
                        }
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "document_id": 1,
                    "question": "What is the main topic of this document?"
                },
                request_only=True
            ),
            OpenApiExample(
                "Example response",
                value={
                    "response": "The document discusses the implementation of a machine learning model..."
                },
                response_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def generate_response(self, request):
        """
        Generate an AI response using the specified document as context.
        """
        serializer = PromptSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        document_id = serializer.validated_data['document_id']
        question = serializer.validated_data['question']

        try:
            # Document retrieval is kept to confirm document existence,
            # and potentially for metadata, though Chroma query will fetch actual chunks.
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        relevant_paragraphs = [] # Initialize to empty list

        # --- Start of ChromaDB Query Integration ---
        try:
            # Ensure Gemini API is configured (similar to perform_create)
            if not settings.GEMINI_API_KEY:
                print("GEMINI_API_KEY not found in settings.")
                return Response({"error": "API key not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Configure GenAI if not already (basic check)
            try:
                genai.get_model("models/gemini-1.5-pro-002") # Check if model access implies configuration
            except Exception:
                print("Configuring Gemini API key in generate_response.")
                genai.configure(api_key=settings.GEMINI_API_KEY)

            # 1. Generate embedding for the question
            #    Use the imported 'get_embeddings_for_texts' (which is 'generate_embeddings' from vector_store.py)
            #    Pass the question as a list, and specify task_type for querying.
            question_embedding = get_embeddings_for_texts(
                texts=[question],
                task_type="retrieval_query" # Crucial for effective RAG
            )

            if not question_embedding: # Should be a list containing one embedding
                return Response({"error": "Failed to generate question embedding."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 2. Get ChromaDB collection
            chroma_client = get_chroma_client()
            collection = get_or_create_collection(client=chroma_client)

            # 3. Query ChromaDB
            #    Query for top_k (e.g., 5) relevant chunks from the specified document.
            num_results = 5 # Number of relevant chunks to retrieve
            query_results = collection.query(
                query_embeddings=question_embedding, # Chroma expects a list of embeddings
                n_results=num_results,
                where={"document_id": str(document_id)} # Filter by document_id from metadata
            )
            
            if query_results and query_results.get('documents') and query_results['documents'][0]:
                relevant_paragraphs = query_results['documents'][0]
            else:
                print(f"No relevant chunks found in ChromaDB for document {document_id} and question: {question}")

        except Exception as e:
            print(f"Error during ChromaDB query or question embedding: {e}")
            return Response({"error": f"Failed to retrieve relevant context: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # --- End of ChromaDB Query Integration ---
        
        try:
            # Use a stable Gemini model
            model_name = "models/gemini-1.5-pro-002"  
            print(f"\nUsing model: {model_name}")
            
            model = genai.GenerativeModel(model_name)
            
            separator = '-' * 40
            if not relevant_paragraphs: 
                prompt_context = "No specific context sections were found in the document for this query."
            else:
                prompt_context = '\n\n'.join(relevant_paragraphs)

            prompt = f"""
Based on the following relevant sections from the documentation:

{separator}
{prompt_context}
{separator}

Please answer this question:
{question}

Note: If the provided sections don't contain enough information to answer the question accurately, 
please indicate that in your response.
"""
            # Print the prompt being sent to Gemini API
            print("\nSending the following prompt to Gemini API:")
            print("=" * 80)
            print(prompt)
            print("=" * 80)
            print("\nRelevant paragraphs used:")
            for i, p in enumerate(relevant_paragraphs, 1): 
                print(f"\nParagraph {i}:")
                print("-" * 40)
                print(p)
                print("-" * 40)

            # Add retry logic for rate limits
            max_retries = 3
            retry_delay = 5  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(prompt)
                    return Response({
                        "response": response.text,
                        "relevant_sections": relevant_paragraphs
                    })
                except Exception as e:
                    if "quota" in str(e).lower() and attempt < max_retries - 1:
                        print(f"Rate limit hit, waiting {retry_delay} seconds before retry...")
                        time.sleep(retry_delay) # Ensure time is imported
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise e # Re-raise the exception if it's not a quota issue or retries exhausted
            
            return Response(
                {"error": "Failed to generate response after multiple attempts due to API issues."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {"error": f"Error generating response with LLM: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )