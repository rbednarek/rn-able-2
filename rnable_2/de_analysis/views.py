from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from core.models import AnalysisSession
from .models import PCAResult, DEAnalysisResult
import math
import pandas as pd
import numpy as np
import json
import uuid
import gzip
import io
from io import StringIO
from utils import *


def analysis_page(request):
    """
    Main DE analysis page
    Loads existing session if session_id provided in URL
    """
    session_id = request.GET.get("session_id") or request.GET.get("session")
    context = {}

    if session_id:
        # Load existing session
        try:
            session = AnalysisSession.objects.get(session_id=session_id)
            context["session_id"] = session_id
            context["session"] = session

            # Load PCA if exists
            if hasattr(session, "pca_result"):
                pca = session.pca_result
                context["pca_data"] = {
                    "plot_config": pca.plot_config,
                    "pc1_variance": pca.pc1_variance,
                    "pc2_variance": pca.pc2_variance,
                }
                # Expose filenames for client-side export
                context["count_file_name"] = session.count_file_name or ""
                context["metadata_file_name"] = session.metadata_file_name or ""

            # Load DE results if exist
            if session.de_results.exists():
                context["de_results"] = session.de_results.all()

        except AnalysisSession.DoesNotExist:
            context["error"] = "Session not found"

    return render(request, "de_analysis/analysis.html", context)


# ============================================
# API Endpoints
# ============================================


@csrf_exempt
@require_http_methods(["POST"])
def upload_data(request):
    """
    Upload count and metadata files
    Creates new AnalysisSession
    """
    try:
        count_file = request.FILES.get("count_file")
        metadata_file = request.FILES.get("metadata_file")
        experiment_name = request.POST.get("experiment_name", "").strip()

        if not count_file:
            return JsonResponse({"error": "Count file required"}, status=400)

        if not experiment_name:
            return JsonResponse({"error": "Experiment name required"}, status=400)

        # Parse count data
        count_df = parse_uploaded_file(count_file)
        if count_df is None:
            return JsonResponse({"error": "Invalid count file format"}, status=400)

        # Parse metadata if provided
        meta_df = None
        if metadata_file:
            meta_df = parse_uploaded_file(metadata_file)
            if meta_df is None:
                return JsonResponse(
                    {"error": "Invalid metadata file format"}, status=400
                )

        # Create session
        session_id = str(uuid.uuid4())[:8]
        session = AnalysisSession.objects.create(
            session_id=session_id,
            count_data=count_df.to_dict(orient="split"),
            metadata=meta_df.to_dict(orient="split") if meta_df is not None else None,
            user=request.user if request.user.is_authenticated else None,
            name=experiment_name,
            count_file_name=count_file.name,
            metadata_file_name=metadata_file.name if metadata_file else "",
        )

        return JsonResponse(
            {
                "success": True,
                "session_id": session_id,
                "redirect_url": f"/de-analysis/?session={session_id}",
                "samples": list(count_df.columns),
                "genes": len(count_df),
                "count_file_name": count_file.name,
                "metadata_file_name": metadata_file.name if metadata_file else None,
                "experiment_name": experiment_name,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def run_pca_analysis(request):
    """
    Run PCA analysis on uploaded data
    """
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")

        session = get_object_or_404(AnalysisSession, session_id=session_id)

        # Load data from session
        count_df = pd.DataFrame(
            data=session.count_data["data"],
            index=session.count_data["index"],
            columns=session.count_data["columns"],
        )

        meta_df = None
        col1 = None
        col2 = None
        if session.metadata:
            meta_df = pd.DataFrame(
                data=session.metadata["data"],
                index=session.metadata["index"],
                columns=session.metadata["columns"],
            )
            col1 = meta_df.columns[0] if len(meta_df.columns) > 0 else None
            col2 = meta_df.columns[1] if len(meta_df.columns) > 1 else None

        # Run PCA
        pca_df, pc1_var, pc2_var = plot_count_pca(
            count_df=count_df, plot=False, meta_df=meta_df, col1=col1, col2=col2
        )

        # Prepare plot configuration
        plot_config = prepare_plotly_config(pca_df, meta_df, col1, col2)

        # Save PCA result
        pca_result, created = PCAResult.objects.update_or_create(
            session=session,
            defaults={
                "pca_coordinates": pca_df.to_dict(orient="split"),
                "pc1_variance": pc1_var,
                "pc2_variance": pc2_var,
                "plot_config": plot_config,
            },
        )

        return JsonResponse(
            {
                "success": True,
                "plot_config": plot_config,
                "pc1_variance": pc1_var,
                "pc2_variance": pc2_var,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def run_de_analysis_api(request):
    """
    Run differential expression analysis
    Groups are now passed in the request body instead of loaded from PCA
    """
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")

        # Get group definitions from request
        control_group_name = data.get("control_group_name")
        treatment_group_name = data.get("treatment_group_name")
        control_samples = data.get("control_samples", [])
        treatment_samples = data.get("treatment_samples", [])

        # Validate inputs
        if not all(
            [
                control_group_name,
                treatment_group_name,
                control_samples,
                treatment_samples,
            ]
        ):
            return JsonResponse(
                {"error": "Missing required group information"}, status=400
            )

        session = get_object_or_404(AnalysisSession, session_id=session_id)

        # Get PCA result if it exists (optional - for linking)
        pca_result = None
        if hasattr(session, "pca_result"):
            pca_result = session.pca_result

        # Load data
        count_df = pd.DataFrame(
            data=session.count_data["data"],
            index=session.count_data["index"],
            columns=session.count_data["columns"],
        )

        meta_df = (
            pd.DataFrame(
                data=session.metadata["data"],
                index=session.metadata["index"],
                columns=session.metadata["columns"],
            )
            if session.metadata
            else None
        )

        # Filter to selected samples
        all_samples = control_samples + treatment_samples
        count_filtered = count_df[all_samples]

        # Create metadata with group assignments
        if meta_df is not None:
            meta_filtered = meta_df.loc[all_samples].copy()
        else:
            # Create minimal metadata if none exists
            meta_filtered = pd.DataFrame(index=all_samples)

        # Add group column
        meta_filtered["group"] = ""
        for sample in control_samples:
            meta_filtered.at[sample, "group"] = control_group_name
        for sample in treatment_samples:
            meta_filtered.at[sample, "group"] = treatment_group_name

        # Run DE analysis
        results_df = run_de_analysis(
            count_filtered,
            meta_filtered,
            control_group_name,
            treatment_group_name,
        )

        # Save results with group definitions
        sanitized_results = _dataframe_to_json(results_df)
        de_result = DEAnalysisResult.objects.create(
            session=session,
            pca_result=pca_result,  # Link to PCA if it exists
            control_group=control_group_name,
            treatment_group=treatment_group_name,
            control_samples=control_samples,
            treatment_samples=treatment_samples,
            results_data=sanitized_results,
            results_csv=results_df.to_csv(),
            metadata_csv=meta_filtered.to_csv(),
            source="generated",
        )

        return JsonResponse(
            {
                "success": True,
                "result_id": de_result.id,
                "n_genes": len(results_df),
                "n_significant": de_result.n_significant,
                "enrichment_url": f"/enrichment/?session={session_id}&de_result={de_result.id}",
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _dataframe_to_json(df):
    """Convert DataFrame to dict with JSON-friendly values."""
    safe_df = df.replace([np.nan, np.inf, -np.inf], None)
    payload = safe_df.to_dict(orient="split")
    return _convert_value(payload)


def _convert_value(value):
    """Recursively convert values to JSON-friendly primitives."""
    if isinstance(value, dict):
        return {k: _convert_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_convert_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_convert_value(v) for v in value)
    if isinstance(value, np.generic):
        return value.item()
    if (
        isinstance(value, (float, int))
        and isinstance(value, float)
        and not math.isfinite(value)
    ):
        return None
    if pd.isna(value):
        return None
    return value


@require_http_methods(["GET"])
def download_results(request, result_id):
    """Download DE analysis results as CSV"""
    de_result = get_object_or_404(DEAnalysisResult, id=result_id)

    file_type = request.GET.get("type", "results")

    if file_type == "metadata":
        content = de_result.metadata_csv
        filename = (
            f"{de_result.treatment_group}_v_{de_result.control_group}_metadata.csv"
        )
    else:
        content = de_result.results_csv
        filename = (
            f"{de_result.treatment_group}_v_{de_result.control_group}_de_results.csv"
        )

    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ============================================
# Helper Functions
# ============================================


def parse_uploaded_file(file):
    """Parse uploaded CSV/TSV file"""
    try:
        filename = file.name
        content = file.read()

        # Determine separator
        if filename.endswith(".tsv") or filename.endswith(".tsv.gz"):
            sep = "\t"
        else:
            sep = ","

        # Handle gzip
        if filename.endswith(".gz"):
            with gzip.open(io.BytesIO(content), "rt", encoding="utf-8") as f:
                df = pd.read_csv(f, sep=sep, index_col=0)
        else:
            df = pd.read_csv(StringIO(content.decode("utf-8")), sep=sep, index_col=0)

        return df
    except Exception as e:
        print(f"Error parsing file: {e}")
        return None


def prepare_plotly_config(pca_df, meta_df, col1, col2):
    """Prepare Plotly configuration for PCA plot"""
    config = {
        "samples": pca_df.index.tolist(),
        "pc1": pca_df["PC1"].tolist(),
        "pc2": pca_df["PC2"].tolist(),
    }

    if meta_df is not None and col1:
        config["metadata"] = {
            col1: meta_df[col1].tolist(),
        }
        if col2:
            config["metadata"][col2] = meta_df[col2].tolist()
        config["metadata_columns"] = [col1, col2] if col2 else [col1]

    return config
