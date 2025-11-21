from collections import OrderedDict

import numpy as np
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from de_analysis.models import DEAnalysisResult


def index(request):
    """Render enrichment page with available sessions."""
    session_ids = _get_sessions_with_results()
    return render(request, "enrichment/index.html", {"session_ids": session_ids})


def _get_sessions_with_results():
    """Return session_ids that have at least one DE analysis."""
    seen = OrderedDict()
    results = (
        DEAnalysisResult.objects.select_related("session")
        .order_by("-created_at")
        .only("session__session_id")
    )
    for result in results:
        session_id = result.session.session_id
        if session_id not in seen:
            seen[session_id] = True
    return list(seen.keys())


@require_http_methods(["GET"])
def session_de_data(request, session_id):
    """Return padj/log2FoldChange pairs for the latest DE run in a session."""
    result = (
        DEAnalysisResult.objects.filter(session__session_id=session_id)
        .order_by("-created_at")
        .first()
    )

    if not result:
        return JsonResponse(
            {"error": "No differential expression results found for this session"},
            status=404,
        )

    df = result.to_dataframe()
    required_cols = ["padj", "log2FoldChange"]
    if not all(col in df.columns for col in required_cols):
        return JsonResponse(
            {"error": f"Required columns missing: {required_cols}"}, status=400
        )

    df = (
        df[required_cols]
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=required_cols)
    )

    payload = {
        "session_id": session_id,
        "result_id": result.id,
        "padj": df["padj"].tolist(),
        "log2FoldChange": df["log2FoldChange"].tolist(),
        "genes": df.index.tolist(),
    }

    return JsonResponse(payload)
