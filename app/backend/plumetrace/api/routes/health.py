"""Health endpoint."""

from fastapi import APIRouter

import plumetrace
from plumetrace.api.schemas import Health

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> Health:
    """Report that the server is up.

    Returns:
        Status ``ok`` and the package version.
    """
    return Health(status="ok", version=plumetrace.__version__)
