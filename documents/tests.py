from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
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

    def test_find_relevant_paragraphs(self):
        """Test the find_relevant_paragraphs method"""
        # Test with a query about attacking
        query = "How many dice are rolled when attacking?"
        paragraphs = self.view.split_into_paragraphs(self.test_content)
        relevant = self.view.find_relevant_paragraphs(paragraphs, query)
        
        # Should find the paragraph about attacking
        self.assertTrue(any("roll 2 dice" in p for p in relevant))
        
        # Test with a query about combat
        query = "How does combat work?"
        relevant = self.view.find_relevant_paragraphs(paragraphs, query)
        
        # Should find the paragraph about combat
        self.assertTrue(any("Combat is resolved" in p for p in relevant))

    def test_find_relevant_paragraphs_with_keywords(self):
        """Test keyword matching in find_relevant_paragraphs"""
        paragraphs = self.view.split_into_paragraphs(self.test_content)
        
        # Test with specific keywords
        query = "dice attack modifier"
        relevant = self.view.find_relevant_paragraphs(paragraphs, query)
        
        # Should find the paragraph with both dice and attack
        self.assertTrue(any("roll 2 dice" in p and "attack modifier" in p for p in relevant))

    def test_find_relevant_paragraphs_with_context(self):
        """Test that relevant paragraphs include proper context"""
        paragraphs = self.view.split_into_paragraphs(self.test_content)
        query = "What happens when an attack hits?"
        relevant = self.view.find_relevant_paragraphs(paragraphs, query)
        
        # Should include both the dice rolling and hit condition
        relevant_text = ' '.join(relevant)
        self.assertTrue("roll 2 dice" in relevant_text or "attack hits" in relevant_text)

    def test_document_upload(self):
        """Test document upload endpoint"""
        url = '/api/documents/'
        
        # Create a new test file for upload
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(self.test_content.encode())
            tmp_file.flush()
            
            with open(tmp_file.name, 'rb') as file:
                data = {
                    'title': 'Test Upload',
                    'file': file
                }
                
                response = self.client.post(url, data, format='multipart')
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                
                # Verify the document was created
                self.assertTrue(Document.objects.filter(title='Test Upload').exists())
                
                # Clean up
                os.unlink(tmp_file.name)

    def test_generate_response(self):
        """Test the generate_response endpoint"""
        url = '/api/documents/generate_response/'
        data = {
            'document_id': self.document.id,
            'question': 'How many dice are rolled when attacking?'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify the response contains relevant information
        self.assertIn('response', response.data)
        self.assertIn('relevant_sections', response.data)
        
        # Verify the relevant sections contain the dice information
        relevant_sections = response.data['relevant_sections']
        self.assertTrue(any('roll 2 dice' in section for section in relevant_sections))

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