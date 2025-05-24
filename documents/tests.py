from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from rest_framework import status
from .models import Document
from .views import DocumentViewSet
import os
import tempfile

class DocumentViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.view = DocumentViewSet()
        
        # Create a test document
        self.test_content = """
        Section 1: Introduction
        This is the introduction section of the document.
        
        Section 2: Game Rules
        When attacking, roll 2 dice. Add your attack modifier to the result.
        If the total is higher than the target's defense, the attack hits.
        
        Section 3: Combat
        Combat is resolved in turns. Each player takes their turn in order.
        During your turn, you can move and perform one action.
        """
        
        # Create a test file
        self.test_file = SimpleUploadedFile(
            "test.txt",
            self.test_content.encode(),
            content_type="text/plain"
        )
        
        # Create a document instance
        self.document = Document.objects.create(
            title="Test Document",
            file=self.test_file
        )
        self.document.content = self.test_content
        self.document.save()

    def test_split_into_paragraphs(self):
        """Test the split_into_paragraphs method"""
        paragraphs = self.view.split_into_paragraphs(self.test_content)
        
        # Should split into 3 main paragraphs
        self.assertEqual(len(paragraphs), 3)
        
        # Each paragraph should contain its section header
        self.assertIn("Section 1", paragraphs[0])
        self.assertIn("Section 2", paragraphs[1])
        self.assertIn("Section 3", paragraphs[2])

    # Obsolete tests removed:
    # test_find_relevant_paragraphs
    # test_find_relevant_paragraphs_with_keywords
    # test_find_relevant_paragraphs_with_context

    @patch('documents.views.get_embeddings_for_texts')
    @patch('documents.views.get_or_create_collection')
    def test_document_upload(self, mock_get_collection_upload, mock_get_embeddings_upload):
        """Test document upload endpoint with ChromaDB/Gemini calls mocked."""
        # Configure mocks
        mock_upload_collection = MagicMock()
        mock_get_collection_upload.return_value = mock_upload_collection
        # Simulate embedding generation returning a list of embeddings (e.g., one per paragraph)
        mock_get_embeddings_upload.return_value = [[0.1, 0.2, 0.3]] 

        url = '/api/documents/'
        
        # Create a new test file for upload
        # Using a temporary file for the upload process
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(self.test_content.encode())
            tmp_file.seek(0) # Rewind to the beginning of the file before reading
            
            data = {
                'title': 'Test Upload',
                'file': tmp_file # Pass the file object directly
            }
            
            response = self.client.post(url, data, format='multipart')
        
        # Clean up the temporary file
        os.unlink(tmp_file.name)
                
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify the document was created
        uploaded_doc = Document.objects.filter(title='Test Upload').first()
        self.assertIsNotNone(uploaded_doc)
        
        # Verify mocks were called (basic checks)
        mock_get_embeddings_upload.assert_called() # Check if it was called
        mock_upload_collection.add.assert_called() # Check if add was called on the collection

    @patch('documents.views.get_embeddings_for_texts') # Mocks the function in views.py that calls Gemini for embeddings
    @patch('documents.views.get_or_create_collection') # Mocks ChromaDB collection retrieval
    @patch('documents.views.genai.GenerativeModel')    # Mocks the Gemini LLM
    def test_generate_response(self, MockGenerativeModel, mock_get_collection, mock_get_embeddings):
        """Test the generate_response endpoint with ChromaDB and Gemini mocked."""
        
        # --- Mock Gemini Embedding Generation ---
        # Simulate question embedding
        mock_get_embeddings.return_value = [[0.1, 0.2, 0.3]] # Example question embedding

        # --- Mock ChromaDB ---
        mock_collection = MagicMock()
        # Simulate ChromaDB query result, ensure 'documents' is a list of lists as query() returns
        mock_collection.query.return_value = {
            'documents': [['When attacking, roll 2 dice. Add your attack modifier to the result.']] 
        }
        mock_get_collection.return_value = mock_collection

        # --- Mock Gemini LLM Response ---
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_content.return_value = MagicMock(text="The AI says: Roll 2 dice when attacking.")
        MockGenerativeModel.return_value = mock_llm_instance
        
        # --- Make the API Call ---
        url = '/api/documents/generate_response/'
        data = {
            'document_id': self.document.id,
            'question': 'How many dice are rolled when attacking?'
        }
        
        response = self.client.post(url, data, format='json')
        
        # --- Assertions ---
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
        self.assertEqual(response.data['response'], "The AI says: Roll 2 dice when attacking.")
        self.assertIn('relevant_sections', response.data)
        # Check that the relevant section from mocked ChromaDB is present
        self.assertTrue(any('roll 2 dice' in section for section in response.data['relevant_sections']))

        # --- Verify mock calls (optional but good practice) ---
        # Verify get_embeddings_for_texts was called for the question
        mock_get_embeddings.assert_called_with(texts=[data['question']], task_type='retrieval_query')
        
        # Verify ChromaDB query
        mock_collection.query.assert_called_once_with(
            query_embeddings=[[0.1, 0.2, 0.3]], # The mocked question embedding
            n_results=5, # Default n_results in views.py
            where={'document_id': str(self.document.id)}
        )
        
        # Verify LLM call
        # This requires checking the prompt, which can be complex.
        # For simplicity, just check it was called.
        mock_llm_instance.generate_content.assert_called_once()
        # More advanced: capture the prompt and assert its content.
        # prompt_arg = mock_llm_instance.generate_content.call_args[0][0]
        # self.assertIn("When attacking, roll 2 dice.", prompt_arg)
        # self.assertIn(data['question'], prompt_arg)

    def test_generate_response_invalid_document(self):
        """Test generate_response with invalid document ID"""
        url = '/api/documents/generate_response/'
        data = {
            'document_id': 999,  # Non-existent document
            'question': 'How many dice are rolled when attacking?'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generate_response_missing_question(self):
        """Test generate_response with missing question"""
        url = '/api/documents/generate_response/'
        data = {
            'document_id': self.document.id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def tearDown(self):
        # Clean up test files
        if os.path.exists(self.document.file.path):
            os.remove(self.document.file.path) 