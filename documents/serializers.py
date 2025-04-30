from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'content', 'uploaded_at']
        read_only_fields = ['content', 'uploaded_at']

    def validate_file(self, value):
        """
        Validate that the uploaded file is either a text file or PDF.
        """
        if not (value.name.endswith('.txt') or value.name.endswith('.pdf')):
            raise serializers.ValidationError("Only .txt and .pdf files are allowed.")
        return value

class PromptSerializer(serializers.Serializer):
    document_id = serializers.IntegerField(
        help_text="ID of the document to use for context"
    )
    question = serializers.CharField(
        max_length=1000,
        help_text="Question to ask about the document content"
    ) 