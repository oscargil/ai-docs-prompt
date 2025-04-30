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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

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

    def find_relevant_paragraphs(self, paragraphs, query, top_k=3):
        """Find the most relevant paragraphs using TF-IDF and keyword matching."""
        if not paragraphs:
            return []
        
        # Extract keywords from the query
        query_keywords = set(word.lower() for word in query.split() if len(word) > 3)
        
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(stop_words='english')
        
        try:
            # Create document-term matrix
            tfidf_matrix = vectorizer.fit_transform(paragraphs)
            # Transform query
            query_vector = vectorizer.transform([query])
            
            # Calculate similarity scores
            similarity_scores = cosine_similarity(query_vector, tfidf_matrix)
            
            # Get indices of top-k most similar paragraphs
            top_indices = similarity_scores[0].argsort()[-top_k:][::-1]
            
            # Score paragraphs based on both TF-IDF and keyword presence
            paragraph_scores = []
            for i in top_indices:
                paragraph = paragraphs[i]
                # Count matching keywords
                keyword_matches = sum(1 for word in paragraph.lower().split() 
                                    if word in query_keywords)
                
                # Combine TF-IDF score with keyword matches
                combined_score = similarity_scores[0][i] * (1 + keyword_matches * 0.2)
                paragraph_scores.append((combined_score, i))
            
            # Sort by combined score
            paragraph_scores.sort(reverse=True)
            
            # Return the most relevant paragraphs
            relevant_paragraphs = []
            for score, i in paragraph_scores:
                paragraph = paragraphs[i]
                # Split into sentences
                sentences = [s.strip() for s in paragraph.split('.') if s.strip()]
                
                if sentences:
                    # Find sentences with keywords
                    keyword_sentences = []
                    for sentence in sentences:
                        if any(word in sentence.lower() for word in query_keywords):
                            keyword_sentences.append(sentence)
                    
                    if keyword_sentences:
                        # Include context around keyword sentences
                        context = []
                        for sentence in sentences:
                            if sentence in keyword_sentences:
                                # Add the sentence and its neighbors
                                idx = sentences.index(sentence)
                                start = max(0, idx - 2)
                                end = min(len(sentences), idx + 3)
                                context.extend(sentences[start:end])
                        
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_context = []
                        for s in context:
                            if s not in seen:
                                seen.add(s)
                                unique_context.append(s)
                        
                        relevant_paragraphs.append('. '.join(unique_context) + '.')
                    else:
                        # If no keyword matches, use the whole paragraph
                        relevant_paragraphs.append(paragraph)
                else:
                    relevant_paragraphs.append(paragraph)
            
            return relevant_paragraphs
        except Exception as e:
            print(f"Error in finding relevant paragraphs: {e}")
            # If there's an error, return the first 3 paragraphs as fallback
            return paragraphs[:3]

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
                    content += page.extract_text() + "\n"
            else:
                raise ValueError("Unsupported file type")
            
            document.content = content
            document.save()
        except Exception as e:
            print(f"Error extracting content: {e}")

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
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Split document into paragraphs and find relevant ones
        paragraphs = self.split_into_paragraphs(document.content)
        relevant_paragraphs = self.find_relevant_paragraphs(paragraphs, question)

        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        try:
            # Use a stable Gemini model
            model_name = "models/gemini-1.5-pro-002"  # Using the latest stable version
            print(f"\nUsing model: {model_name}")
            
            model = genai.GenerativeModel(model_name)
            
            # Create a prompt that includes only the relevant paragraphs
            separator = '-' * 40
            prompt = """
            Based on the following relevant sections from the documentation:

            {separator}
            {paragraphs}
            {separator}

            Please answer this question:
            {question}

            Note: If the provided sections don't contain enough information to answer the question accurately, 
            please indicate that in your response.
            """.format(
                separator=separator,
                paragraphs='\n\n'.join(relevant_paragraphs),
                question=question
            )

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
                        "relevant_sections": relevant_paragraphs  # Include the relevant sections in response
                    })
                except Exception as e:
                    if "quota" in str(e).lower() and attempt < max_retries - 1:
                        print(f"Rate limit hit, waiting {retry_delay} seconds before retry...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise e
            
            return Response(
                {"error": "Failed to generate response after multiple attempts"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {"error": f"Error generating response: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 