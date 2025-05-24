import unittest
from unittest.mock import patch, MagicMock
from .vector_store import generate_embeddings, EMBEDDING_MODEL

# Mocking google.generativeai module if it's not already available in the test environment
# or to control its behavior directly.
# If 'google.generativeai' is importable but we want to mock its methods,
# we can patch 'documents.vector_store.genai'.

class TestGenerateEmbeddings(unittest.TestCase):

    @patch('documents.vector_store.genai')
    def test_generate_embeddings_success(self, mock_genai):
        """Test successful embedding generation."""
        mock_genai.embed_content.return_value = {
            'embedding': [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        }
        texts = ["hello world", "another text"]
        task_type = "retrieval_document"
        
        embeddings = generate_embeddings(texts, task_type=task_type, model_name=EMBEDDING_MODEL)
        
        self.assertEqual(len(embeddings), 2)
        self.assertEqual(embeddings[0], [0.1, 0.2, 0.3])
        mock_genai.embed_content.assert_called_once_with(
            model=EMBEDDING_MODEL,
            content=texts,
            task_type=task_type
        )

    def test_generate_embeddings_empty_input(self):
        """Test generate_embeddings with empty input list of texts."""
        embeddings = generate_embeddings([])
        self.assertEqual(embeddings, [])

    @patch('documents.vector_store.genai') # Patch genai even if not strictly used, for consistency
    def test_generate_embeddings_invalid_model_name(self, mock_genai):
        """Test that ValueError is raised for an invalid model name prefix."""
        with self.assertRaisesRegex(ValueError, "Model invalid-model is not a recognized embedding model."):
            generate_embeddings(["test text"], model_name="invalid-model")

    @patch('documents.vector_store.genai')
    def test_generate_embeddings_missing_embedding_key(self, mock_genai):
        """Test ValueError if 'embedding' key is missing in genai response."""
        mock_genai.embed_content.return_value = {'other_key': 'some_value'} # No 'embedding' key
        texts = ["hello world"]
        
        with self.assertRaisesRegex(ValueError, "Embedding not found in genai response."):
            generate_embeddings(texts, model_name=EMBEDDING_MODEL)

    @patch('documents.vector_store.genai')
    def test_generate_embeddings_api_error(self, mock_genai):
        """Test that an exception from genai.embed_content is re-raised."""
        mock_genai.embed_content.side_effect = Exception("Gemini API Error")
        texts = ["hello world"]
        
        with self.assertRaisesRegex(Exception, "Gemini API Error"):
            generate_embeddings(texts, model_name=EMBEDDING_MODEL)

if __name__ == '__main__':
    unittest.main()
