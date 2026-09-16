"""Paket ishga tushganda birinchi bo'lib bajariladi.

SSL sertifikat yo'lini aiohttp import qilinishidan OLDIN o'rnatish shart —
aiohttp o'z SSL kontekstini import paytida keshlaydi.
"""
from __future__ import annotations

import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_BUNDLE = _BASE / ".certs" / "ca-bundle.pem"

if _BUNDLE.exists() and not os.getenv("SSL_CERT_FILE"):
    os.environ["SSL_CERT_FILE"] = str(_BUNDLE)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", str(_BUNDLE))


def ca_bundle() -> str | None:
    """Qo'shimcha CA fayli yo'li (bo'lmasa None)."""
    path = os.getenv("SSL_CERT_FILE")
    return path if path and Path(path).exists() else None
