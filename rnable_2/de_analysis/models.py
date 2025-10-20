from django.db import models
from core.models import AnalysisSession
import pandas as pd
from io import StringIO


class PCAResult(models.Model):
    """
    PCA analysis results for sample clustering
    """

    session = models.OneToOneField(
        AnalysisSession, on_delete=models.CASCADE, related_name="pca_result"
    )

    # PCA data
    pca_coordinates = models.JSONField(help_text="PC1, PC2 coordinates for each sample")
    pc1_variance = models.FloatField(help_text="Variance explained by PC1")
    pc2_variance = models.FloatField(help_text="Variance explained by PC2")

    # Plotly configuration for reproducibility
    plot_config = models.JSONField(help_text="Complete Plotly figure configuration")

    # Sample groups (for DE analysis)
    # group1_samples = models.JSONField(null=True, blank=True)
    # group2_samples = models.JSONField(null=True, blank=True)
    # group1_name = models.CharField(max_length=100, null=True, blank=True)
    # group2_name = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session"]),
        ]

    def __str__(self):
        return f"PCA for {self.session.session_id}"

    def get_plot_url(self):
        """Get shareable URL for this PCA plot"""
        return f"/de-analysis/?session={self.session.session_id}"


class DEAnalysisResult(models.Model):
    """
    Differential expression analysis results
    Can be generated or uploaded
    """

    SOURCE_CHOICES = [
        ("generated", "Generated in RN-able"),
        ("uploaded", "Uploaded by user"),
    ]

    session = models.ForeignKey(
        AnalysisSession, on_delete=models.CASCADE, related_name="de_results"
    )

    # Experiment information
    experiment_tag = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional tag to link this DE analysis to other datasets",
    )

    # Group information
    control_group = models.CharField(max_length=100)
    treatment_group = models.CharField(max_length=100)
    control_samples = models.JSONField()
    treatment_samples = models.JSONField()

    # Results data
    results_data = models.JSONField(help_text="DE results as JSON")
    results_csv = models.TextField(help_text="Results as CSV string")

    # Metadata for samples used
    metadata_csv = models.TextField(blank=True, help_text="Sample metadata CSV")

    # Source tracking
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="generated"
    )

    # Statistics
    n_significant = models.IntegerField(
        default=0, help_text="Number of significant genes"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "-created_at"]),
        ]

    def __str__(self):
        return f"DE: {self.treatment_group} vs {self.control_group}"

    def save(self, *args, **kwargs):
        """Calculate n_significant on save"""
        if self.results_data and not self.n_significant:
            df = pd.DataFrame(self.results_data)
            if "padj" in df.columns and "log2FoldChange" in df.columns:
                self.n_significant = len(
                    df[(df["padj"] < 0.05) & (abs(df["log2FoldChange"]) > 1)]
                )
        super().save(*args, **kwargs)

    def get_significant_genes(self, padj_cutoff=0.05, logfc_cutoff=1):
        """Extract significant genes"""
        df = pd.DataFrame(self.results_data)
        sig_genes = df[
            (df["padj"] < padj_cutoff) & (abs(df["log2FoldChange"]) > logfc_cutoff)
        ]
        return sig_genes.index.tolist()

    def to_dataframe(self):
        """Convert results to DataFrame"""
        return pd.DataFrame(self.results_data)
