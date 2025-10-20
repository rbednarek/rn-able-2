from django.db import models
from django.contrib.auth.models import User
import uuid


class AnalysisSession(models.Model):
    """
    Central session model - stores uploaded data
    Shared across all analysis types
    """

    session_id = models.CharField(
        max_length=100, unique=True, db_index=True, default=uuid.uuid4, editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analysis_sessions",
    )

    # Uploaded data stored as JSON
    count_data = models.JSONField(help_text="Count matrix data")
    metadata = models.JSONField(null=True, blank=True, help_text="Sample metadata")

    # Session info
    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"Session {self.session_id} - {self.name or self.created_at}"

    def get_sample_count(self):
        """Helper to get number of samples"""
        if self.count_data:
            return len(self.count_data.get("columns", []))
        return 0

    def get_gene_count(self):
        """Helper to get number of genes"""
        if self.count_data:
            return len(self.count_data.get("index", []))
        return 0
