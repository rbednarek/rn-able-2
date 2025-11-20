from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import AnalysisSession
from .models import PCAResult, DEAnalysisResult
import pandas as pd
import numpy as np
import json
import io
import gzip


class PCAResultModelTest(TestCase):
    """Test PCAResult model"""

    def setUp(self):
        """Set up test data"""
        self.session = AnalysisSession.objects.create(
            session_id="test123",
            count_data={
                "data": [[1, 2, 3], [4, 5, 6]],
                "index": ["gene1", "gene2"],
                "columns": ["sample1", "sample2", "sample3"],
            },
            name="Test Session",
        )

    def test_pca_result_creation(self):
        """Test creating a PCA result"""
        pca_data = {
            "data": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "index": ["sample1", "sample2", "sample3"],
            "columns": ["PC1", "PC2"],
        }
        pca_result = PCAResult.objects.create(
            session=self.session,
            pca_coordinates=pca_data,
            pc1_variance=45.5,
            pc2_variance=30.2,
            plot_config={"samples": ["sample1", "sample2", "sample3"]},
        )
        self.assertEqual(pca_result.session, self.session)
        self.assertEqual(pca_result.pc1_variance, 45.5)
        self.assertEqual(pca_result.pc2_variance, 30.2)

    def test_pca_result_str(self):
        """Test PCAResult string representation"""
        pca_result = PCAResult.objects.create(
            session=self.session,
            pca_coordinates={"data": [], "index": [], "columns": []},
            pc1_variance=45.5,
            pc2_variance=30.2,
            plot_config={},
        )
        self.assertIn("test123", str(pca_result))

    def test_pca_result_get_plot_url(self):
        """Test get_plot_url method"""
        pca_result = PCAResult.objects.create(
            session=self.session,
            pca_coordinates={"data": [], "index": [], "columns": []},
            pc1_variance=45.5,
            pc2_variance=30.2,
            plot_config={},
        )
        url = pca_result.get_plot_url()
        self.assertIn("test123", url)
        self.assertIn("session", url)


class DEAnalysisResultModelTest(TestCase):
    """Test DEAnalysisResult model"""

    def setUp(self):
        """Set up test data"""
        self.session = AnalysisSession.objects.create(
            session_id="test123",
            count_data={
                "data": [[1, 2, 3], [4, 5, 6]],
                "index": ["gene1", "gene2"],
                "columns": ["sample1", "sample2", "sample3"],
            },
            name="Test Session",
        )

    def test_de_result_creation(self):
        """Test creating a DE analysis result"""
        results_data = {
            "data": [[0.5, 0.01, 2.0], [-0.3, 0.05, 1.5]],
            "index": ["gene1", "gene2"],
            "columns": ["log2FoldChange", "padj", "pvalue"],
        }
        de_result = DEAnalysisResult.objects.create(
            session=self.session,
            control_group="Control",
            treatment_group="Treatment",
            control_samples=["sample1"],
            treatment_samples=["sample2", "sample3"],
            results_data=results_data,
            results_csv="gene,log2FoldChange,padj\ngene1,0.5,0.01",
            source="generated",
        )
        self.assertEqual(de_result.session, self.session)
        self.assertEqual(de_result.control_group, "Control")
        self.assertEqual(de_result.treatment_group, "Treatment")

    def test_de_result_n_significant_calculation(self):
        """Test automatic calculation of n_significant"""
        # Create results with some significant genes
        results_data = {
            "data": [
                [2.5, 0.01, 0.001],  # Significant: log2FC > 1, padj < 0.05
                [-1.5, 0.02, 0.002],  # Significant: log2FC < -1, padj < 0.05
                [0.5, 0.10, 0.05],  # Not significant: log2FC < 1
                [2.0, 0.10, 0.05],  # Not significant: padj >= 0.05
            ],
            "index": ["gene1", "gene2", "gene3", "gene4"],
            "columns": ["log2FoldChange", "padj", "pvalue"],
        }
        de_result = DEAnalysisResult.objects.create(
            session=self.session,
            control_group="Control",
            treatment_group="Treatment",
            control_samples=["sample1"],
            treatment_samples=["sample2"],
            results_data=results_data,
            results_csv="test",
        )
        # Should count 2 significant genes
        self.assertEqual(de_result.n_significant, 2)

    def test_de_result_to_dataframe(self):
        """Test converting results to DataFrame"""
        results_data = {
            "data": [[0.5, 0.01], [-0.3, 0.05]],
            "index": ["gene1", "gene2"],
            "columns": ["log2FoldChange", "padj"],
        }
        de_result = DEAnalysisResult.objects.create(
            session=self.session,
            control_group="Control",
            treatment_group="Treatment",
            control_samples=["sample1"],
            treatment_samples=["sample2"],
            results_data=results_data,
            results_csv="test",
        )
        df = de_result.to_dataframe()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("log2FoldChange", df.columns)
        self.assertIn("padj", df.columns)

    def test_de_result_get_significant_genes(self):
        """Test get_significant_genes method"""
        results_data = {
            "data": [
                [2.5, 0.01],  # Significant
                [-1.5, 0.02],  # Significant
                [0.5, 0.10],  # Not significant
            ],
            "index": ["gene1", "gene2", "gene3"],
            "columns": ["log2FoldChange", "padj"],
        }
        de_result = DEAnalysisResult.objects.create(
            session=self.session,
            control_group="Control",
            treatment_group="Treatment",
            control_samples=["sample1"],
            treatment_samples=["sample2"],
            results_data=results_data,
            results_csv="test",
        )
        sig_genes = de_result.get_significant_genes()
        self.assertEqual(len(sig_genes), 2)
        self.assertIn("gene1", sig_genes)
        self.assertIn("gene2", sig_genes)
        self.assertNotIn("gene3", sig_genes)


class DEAnalysisViewsTest(TestCase):
    """Test DE analysis views"""

    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.session = AnalysisSession.objects.create(
            session_id="test123",
            count_data={
                "data": [[10, 20, 30], [40, 50, 60], [70, 80, 90]],
                "index": ["gene1", "gene2", "gene3"],
                "columns": ["sample1", "sample2", "sample3"],
            },
            name="Test Session",
            user=self.user,
        )

    def test_analysis_page_without_session(self):
        """Test analysis page without session_id"""
        response = self.client.get("/de-analysis/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("session", response.context)

    def test_analysis_page_with_session(self):
        """Test analysis page with valid session_id"""
        response = self.client.get("/de-analysis/?session=test123")
        self.assertEqual(response.status_code, 200)
        self.assertIn("session", response.context)
        self.assertEqual(response.context["session"].session_id, "test123")

    def test_analysis_page_with_invalid_session(self):
        """Test analysis page with invalid session_id"""
        response = self.client.get("/de-analysis/?session=invalid")
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)

    def test_analysis_page_with_pca_result(self):
        """Test analysis page loads PCA result"""
        PCAResult.objects.create(
            session=self.session,
            pca_coordinates={"data": [], "index": [], "columns": []},
            pc1_variance=45.5,
            pc2_variance=30.2,
            plot_config={"samples": ["sample1", "sample2", "sample3"]},
        )
        response = self.client.get("/de-analysis/?session=test123")
        self.assertEqual(response.status_code, 200)
        self.assertIn("pca_data", response.context)

    def test_upload_data_missing_count_file(self):
        """Test upload endpoint with missing count file"""
        response = self.client.post(
            "/de-analysis/api/upload/",
            {"experiment_name": "Test Experiment"},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)

    def test_upload_data_missing_experiment_name(self):
        """Test upload endpoint with missing experiment name"""
        count_file = SimpleUploadedFile(
            "counts.csv", b"gene,sample1,sample2\ngene1,10,20", content_type="text/csv"
        )
        response = self.client.post(
            "/de-analysis/api/upload/", {"count_file": count_file}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)

    def test_upload_data_success(self):
        """Test successful file upload"""
        count_file = SimpleUploadedFile(
            "counts.csv",
            b"gene,sample1,sample2\ngene1,10,20\ngene2,30,40",
            content_type="text/csv",
        )
        metadata_file = SimpleUploadedFile(
            "metadata.csv",
            b"sample,condition\nsample1,control\nsample2,treatment",
            content_type="text/csv",
        )
        response = self.client.post(
            "/de-analysis/api/upload/",
            {
                "count_file": count_file,
                "metadata_file": metadata_file,
                "experiment_name": "Test Experiment",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertIn("session_id", data)
        # Verify session was created
        session = AnalysisSession.objects.get(session_id=data["session_id"])
        self.assertEqual(session.name, "Test Experiment")

    def test_upload_data_tsv_format(self):
        """Test uploading TSV file"""
        tsv_file = SimpleUploadedFile(
            "counts.tsv",
            b"gene\tsample1\tsample2\ngene1\t10\t20",
            content_type="text/tab-separated-values",
        )
        response = self.client.post(
            "/de-analysis/api/upload/",
            {"count_file": tsv_file, "experiment_name": "Test"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

    def test_download_results(self):
        """Test downloading DE results as CSV"""
        de_result = DEAnalysisResult.objects.create(
            session=self.session,
            control_group="Control",
            treatment_group="Treatment",
            control_samples=["sample1"],
            treatment_samples=["sample2"],
            results_data={"data": [], "index": [], "columns": []},
            results_csv="gene,log2FoldChange,padj\ngene1,0.5,0.01",
            metadata_csv="sample,group\nsample1,Control",
        )
        response = self.client.get(f"/de-analysis/api/download/{de_result.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_download_results_metadata(self):
        """Test downloading metadata CSV"""
        de_result = DEAnalysisResult.objects.create(
            session=self.session,
            control_group="Control",
            treatment_group="Treatment",
            control_samples=["sample1"],
            treatment_samples=["sample2"],
            results_data={"data": [], "index": [], "columns": []},
            results_csv="test",
            metadata_csv="sample,group\nsample1,Control",
        )
        response = self.client.get(
            f"/de-analysis/api/download/{de_result.id}/?type=metadata"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("metadata", response["Content-Disposition"])


class DEAnalysisUtilityFunctionsTest(TestCase):
    """Test utility functions"""

    def setUp(self):
        """Set up test data"""
        self.count_df = pd.DataFrame(
            {
                "sample1": [10, 20, 30, 40],
                "sample2": [15, 25, 35, 45],
                "sample3": [12, 22, 32, 42],
            },
            index=["gene1", "gene2", "gene3", "gene4"],
        )

    def test_parse_uploaded_file_csv(self):
        """Test parsing CSV file"""
        from de_analysis.views import parse_uploaded_file

        csv_content = b"gene,sample1,sample2\ngene1,10,20\ngene2,30,40"
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        df = parse_uploaded_file(csv_file)
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 2)
        self.assertEqual(len(df.columns), 2)

    def test_parse_uploaded_file_tsv(self):
        """Test parsing TSV file"""
        from de_analysis.views import parse_uploaded_file

        tsv_content = b"gene\tsample1\tsample2\ngene1\t10\t20"
        tsv_file = SimpleUploadedFile(
            "test.tsv", tsv_content, content_type="text/tab-separated-values"
        )
        df = parse_uploaded_file(tsv_file)
        self.assertIsNotNone(df)
        self.assertEqual(len(df.columns), 2)

    def test_prepare_plotly_config_basic(self):
        """Test preparing Plotly config without metadata"""
        from de_analysis.views import prepare_plotly_config

        pca_df = pd.DataFrame(
            {"PC1": [1.0, 2.0, 3.0], "PC2": [4.0, 5.0, 6.0]},
            index=["sample1", "sample2", "sample3"],
        )
        config = prepare_plotly_config(pca_df, None, None, None)
        self.assertIn("samples", config)
        self.assertIn("pc1", config)
        self.assertIn("pc2", config)
        self.assertEqual(len(config["samples"]), 3)

    def test_prepare_plotly_config_with_metadata(self):
        """Test preparing Plotly config with metadata"""
        from de_analysis.views import prepare_plotly_config

        pca_df = pd.DataFrame(
            {"PC1": [1.0, 2.0], "PC2": [4.0, 5.0]},
            index=["sample1", "sample2"],
        )
        meta_df = pd.DataFrame(
            {"condition": ["control", "treatment"], "time": ["T0", "T1"]},
            index=["sample1", "sample2"],
        )
        config = prepare_plotly_config(pca_df, meta_df, "condition", "time")
        self.assertIn("metadata", config)
        self.assertIn("condition", config["metadata"])
        self.assertIn("time", config["metadata"])
        self.assertIn("metadata_columns", config)


class PCAFunctionTest(TestCase):
    """Test PCA computation function"""

    def test_plot_count_pca_basic(self):
        """Test basic PCA computation"""
        from utils.de_analysis_fxns import plot_count_pca

        # Create count data with enough variance for PCA
        count_df = pd.DataFrame(
            {
                "sample1": [100, 200, 300],
                "sample2": [150, 250, 350],
                "sample3": [120, 220, 320],
            },
            index=["gene1", "gene2", "gene3"],
        )
        pca_df, pc1_var, pc2_var = plot_count_pca(
            count_df, raw_count=10, min_samples=2, plot=False
        )
        self.assertIsInstance(pca_df, pd.DataFrame)
        self.assertIn("PC1", pca_df.columns)
        self.assertIn("PC2", pca_df.columns)
        self.assertIsInstance(pc1_var, (int, float))
        self.assertIsInstance(pc2_var, (int, float))

    def test_plot_count_pca_with_metadata(self):
        """Test PCA with metadata"""
        from utils.de_analysis_fxns import plot_count_pca

        count_df = pd.DataFrame(
            {
                "sample1": [100, 200],
                "sample2": [150, 250],
            },
            index=["gene1", "gene2"],
        )
        meta_df = pd.DataFrame(
            {"condition": ["control", "treatment"]}, index=["sample1", "sample2"]
        )
        pca_df, pc1_var, pc2_var = plot_count_pca(
            count_df,
            raw_count=10,
            min_samples=1,
            plot=False,
            meta_df=meta_df,
            col1="condition",
        )
        self.assertIsInstance(pca_df, pd.DataFrame)
        # Metadata should be joined to PCA results
        self.assertIn("condition", pca_df.columns)
