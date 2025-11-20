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

    pca_coordinates = models.JSONField(help_text="PC1, PC2 coordinates")
    pc1_variance = models.FloatField()
    pc2_variance = models.FloatField()
    plot_config = models.JSONField(help_text="Plotly config")

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
    DE analysis results - includes the group definitions
    Multiple DE analyses can exist for one PCA!
    """

    SOURCE_CHOICES = [
        ("generated", "Generated in RN-able"),
        ("uploaded", "Uploaded by user"),
    ]

    session = models.ForeignKey(
        AnalysisSession, on_delete=models.CASCADE, related_name="de_results"
    )

    # ADD: Link to PCA (optional - for tracking which PCA was used)
    pca_result = models.ForeignKey(
        PCAResult,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="de_analyses",
    )

    # Group definitions (MOVED from PCAResult)
    control_group = models.CharField(max_length=100)
    treatment_group = models.CharField(max_length=100)
    control_samples = models.JSONField()
    treatment_samples = models.JSONField()

    # Results data
    results_data = models.JSONField()
    results_csv = models.TextField()
    metadata_csv = models.TextField(blank=True)

    # Source tracking
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="generated"
    )

    # Statistics
    n_significant = models.IntegerField(default=0)

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
            try:
                # Handle 'split' orient format
                if isinstance(self.results_data, dict) and "data" in self.results_data:
                    df = pd.DataFrame(
                        data=self.results_data["data"],
                        index=self.results_data["index"],
                        columns=self.results_data["columns"],
                    )
                else:
                    df = pd.DataFrame(self.results_data)

                if "padj" in df.columns and "log2FoldChange" in df.columns:
                    # Count significant genes, handling NaN values
                    sig_mask = (df["padj"] < 0.05) & (df["log2FoldChange"].abs() > 1)
                    self.n_significant = int(sig_mask.sum())
            except Exception as e:
                print(f"Error calculating n_significant: {e}")
                self.n_significant = 0

        super().save(*args, **kwargs)

    def get_significant_genes(self, padj_cutoff=0.05, logfc_cutoff=1):
        """Extract significant genes"""
        df = self.to_dataframe()
        sig_genes = df[
            (df["padj"] < padj_cutoff) & (abs(df["log2FoldChange"]) > logfc_cutoff)
        ]
        return sig_genes.index.tolist()

    def to_dataframe(self):
        """Convert results to DataFrame"""
        if isinstance(self.results_data, dict) and "data" in self.results_data:
            return pd.DataFrame(
                data=self.results_data["data"],
                index=self.results_data["index"],
                columns=self.results_data["columns"],
            )
        return pd.DataFrame(self.results_data)
