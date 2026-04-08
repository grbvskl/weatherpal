"""In-memory conversation flags (minimal; no Redis)."""

from __future__ import annotations

from typing import Literal

PendingKind = Literal["city", "morning"]

pending: dict[int, PendingKind] = {}
