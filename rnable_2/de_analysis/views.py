from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from core.models import AnalysisSession
from .models import PCAResult, DEAnalysisResult
import pandas as pd
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
    session_id = request.GET.get("session")
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
                    # 'group1_samples': pca.group1_samples,
                    # 'group2_samples': pca.group2_samples,
                    # 'group1_name': pca.group1_name,
                    # 'group2_name': pca.group2_name,
                }

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

        if not count_file:
            return JsonResponse({"error": "Count file required"}, status=400)

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
        )

        return JsonResponse(
            {
                "success": True,
                "session_id": session_id,
                "redirect_url": f"/de-analysis/?session={session_id}",
                "samples": list(count_df.columns),
                "genes": len(count_df),
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

        # Run PCA (import your analysis module)
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
def save_groups(request):
    """
    Save selected sample groups from PCA plot
    """
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")

        session = get_object_or_404(AnalysisSession, session_id=session_id)
        pca_result = get_object_or_404(PCAResult, session=session)

        pca_result.group1_samples = data.get("group1_samples", [])
        pca_result.group2_samples = data.get("group2_samples", [])
        pca_result.group1_name = data.get("group1_name", "")
        pca_result.group2_name = data.get("group2_name", "")
        pca_result.save()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def run_de_analysis_api(request):
    """
    Run differential expression analysis
    """
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")

        session = get_object_or_404(AnalysisSession, session_id=session_id)
        pca_result = get_object_or_404(PCAResult, session=session)

        # Load data
        count_df = pd.DataFrame(
            data=session.count_data["data"],
            index=session.count_data["index"],
            columns=session.count_data["columns"],
        )

        meta_df = pd.DataFrame(
            data=session.metadata["data"],
            index=session.metadata["index"],
            columns=session.metadata["columns"],
        )

        # Filter to selected samples
        all_samples = pca_result.group1_samples + pca_result.group2_samples
        count_filtered = count_df[all_samples]
        meta_filtered = meta_df.loc[all_samples].copy()

        # Add group column
        meta_filtered["group"] = ""
        for sample in pca_result.group1_samples:
            meta_filtered.at[sample, "group"] = pca_result.group1_name
        for sample in pca_result.group2_samples:
            meta_filtered.at[sample, "group"] = pca_result.group2_name

        # Run DE analysis (import your analysis module)
        results_df = run_de_analysis(
            count_filtered,
            meta_filtered,
            pca_result.group1_name,
            pca_result.group2_name,
        )

        # Save results
        de_result = DEAnalysisResult.objects.create(
            session=session,
            control_group=pca_result.group1_name,
            treatment_group=pca_result.group2_name,
            control_samples=pca_result.group1_samples,
            treatment_samples=pca_result.group2_samples,
            results_data=results_df.to_dict(orient="split"),
            results_csv=results_df.to_csv(),
            metadata_csv=meta_filtered.to_csv(),
            source="generated",
        )

        # Remove this once we decide to keep raw count data for session
        if session.de_results.exists():
            session.count_data = None
            session.save()

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
