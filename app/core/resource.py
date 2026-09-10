"""Canonical ResourceId contract.

A resource in the policy layer is a *logical* identifier, never a raw operating
system path. The physical mapping (e.g. ``project:agent-os`` -> ``D:\\projects\\Agent``)
lives with whichever executor / device agent actually touches the filesystem,
not here.

Format: ``type:value``

Examples of the intended vocabulary (not all are handled yet):

    project:agent-os
    repo:owner/name
    device:desktop-main
    service:cloudflare
    secretref:openai/main
    task:2f1c...            (a task id)
    local:reasoning         (resource-agnostic local work)

Sprint 1 only needs: a strict canonical form, validation, and no ``*``
full-access escape hatch. Resource-scoped authorization comes later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

KNOWN_RESOURCE_TYPES: frozenset[str] = frozenset(
    {
        "project",
        "repo",
        "device",
        "service",
        "secretref",
        "task",
        "knowledge",
        "local",
    }
)

# lowercase, must start and end alphanumeric, dots/underscores/dashes/slashes inside
_VALUE_RE = re.compile(r"\A[a-z0-9](?:[a-z0-9._/-]{0,198}[a-z0-9])?\Z")


class InvalidResourceId(ValueError):
    """Raised when a string is not a well-formed canonical ResourceId."""


@dataclass(frozen=True)
class ResourceId:
    type: str
    value: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.type}:{self.value}"


def parse_resource_id(raw: object) -> ResourceId:
    """Parse and validate a canonical ResourceId, or raise ``InvalidResourceId``.

    The input must already be in canonical form; this function never "repairs" a
    malformed identifier into a valid one.
    """
    if not isinstance(raw, str):
        raise InvalidResourceId("resource id must be a string")
    if raw != raw.strip() or not raw:
        raise InvalidResourceId("resource id must be non-empty and unpadded")
    if "*" in raw:
        raise InvalidResourceId("'*' is not a valid resource id (no implicit full access)")
    if ".." in raw:
        raise InvalidResourceId("path traversal is not allowed in a resource id")
    if raw.count(":") < 1:
        raise InvalidResourceId("resource id must be 'type:value'")

    rtype, _, value = raw.partition(":")
    if rtype != rtype.lower() or rtype not in KNOWN_RESOURCE_TYPES:
        raise InvalidResourceId(f"unknown or non-canonical resource type: {rtype!r}")
    if not _VALUE_RE.match(value):
        raise InvalidResourceId(f"malformed resource value: {value!r}")
    if rtype == "repo" and value.count("/") != 1:
        raise InvalidResourceId("repo resource must be 'repo:owner/name'")
    if rtype != "repo" and rtype != "secretref" and "/" in value:
        raise InvalidResourceId(f"'/' is not allowed in a {rtype} resource value")
    return ResourceId(rtype, value)


def is_valid_resource_id(raw: object) -> bool:
    try:
        parse_resource_id(raw)
        return True
    except InvalidResourceId:
        return False
