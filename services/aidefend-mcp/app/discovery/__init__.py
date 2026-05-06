"""Discovery-layer integration (read-only).

This package exposes a thin wrapper over the sqlite candidate store produced
by the aidefend-discovery repo. It is *additive* to the official AIDEFEND
surface — discovery records are *never* commingled with AID-* records:

  - Official `AID-*` techniques live in LanceDB and are returned by the 14
    pre-existing tools.
  - Discovery `candidate-*` records live in a separate sqlite database and
    are only returned by the three discovery tools registered here.
  - All discovery responses carry `discovery_namespace: true` and the
    disclaimer string so downstream agents cannot accidentally treat
    hypothesis as official defense.

If `DISCOVERY_DB_PATH` is unset, the discovery tools return graceful
"not configured" responses (no crashes, no silent failures).
"""

from app.discovery.store import (
    DISCOVERY_DISCLAIMER,
    discovery_namespace_response,
    is_discovery_configured,
)

__all__ = [
    "DISCOVERY_DISCLAIMER",
    "discovery_namespace_response",
    "is_discovery_configured",
]
