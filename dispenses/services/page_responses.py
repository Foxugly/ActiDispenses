from __future__ import annotations

from csv import DictWriter
from datetime import datetime
from io import StringIO
from typing import Iterable, Mapping, Sequence

from django.http import HttpResponse


def build_text_download_response(content: str, suffix: str) -> HttpResponse:
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suffix}.txt"
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def build_csv_download_response(
    *,
    rows: Sequence[Mapping[str, object]],
    fieldnames: Iterable[str],
    filename: str,
) -> HttpResponse:
    stream = StringIO()
    writer = DictWriter(stream, fieldnames=list(fieldnames))
    writer.writeheader()
    writer.writerows(rows)
    response = HttpResponse(stream.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
