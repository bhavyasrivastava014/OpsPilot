import unittest
from unittest.mock import Mock, patch

from app.services.gemini_embeddings_service import GeminiEmbeddingsService


class GeminiEmbeddingsServiceTests(unittest.TestCase):
    @patch("app.services.gemini_embeddings_service.SentenceTransformer")
    def test_embed_texts_uses_sentence_transformers(self, sentence_transformer_cls):
        model = Mock()
        model.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
        sentence_transformer_cls.return_value = model

        service = GeminiEmbeddingsService()
        result = service.embed_texts(
            texts=["hello", "world"],
            model="sentence-transformers/all-MiniLM-L6-v2",
        )

        self.assertEqual(result.vectors, [[0.1, 0.2], [0.3, 0.4]])
        sentence_transformer_cls.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")

    @patch("app.services.gemini_embeddings_service.SentenceTransformer")
    def test_legacy_gemini_model_name_is_redirected(self, sentence_transformer_cls):
        model = Mock()
        model.encode.return_value = [[0.1, 0.2]]
        sentence_transformer_cls.return_value = model

        service = GeminiEmbeddingsService()
        service.embed_texts(texts=["hello"], model="models/embedding-004")

        sentence_transformer_cls.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")


if __name__ == "__main__":
    unittest.main()
