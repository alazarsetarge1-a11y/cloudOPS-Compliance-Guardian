"""Shared FastAPI dependencies.

`get_session` is the single place the API resolves AWS credentials — no route
hardcodes them, and tests swap it out wholesale (see backend/tests). It's driven
by env vars rather than CLI args (a web process has no argv):

    CCG_AWS_PROFILE      base profile, e.g. "ccg"; unset -> default cred chain
    CCG_ASSUME_ROLE_ARN  role to assume (e.g. OrganizationAccountAccessRole); optional
    CCG_AWS_REGION       default us-east-1

In production on ECS the task role *is* the member-account identity, so the
default chain works with no assume-role. Locally you set the two CCG_* vars to
assume into the member account — the same hub-and-spoke pattern the detective
runner's CLI uses.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Annotated

import boto3
from fastapi import Depends

from detective.checks.base import Finding
from detective.runner import run_all_checks

# A full scan sweeps every region and is slow. The dashboard loads /findings AND
# /compliance-score together (and dev StrictMode double-fetches), so without this
# a single page load would trigger several serial scans. Cache the scan result
# briefly so those requests reuse one scan. Single-account app -> a global key is
# safe; 60s freshness is fine for a compliance dashboard.
_SCAN_TTL_SECONDS = 60.0
_scan_cache: dict[str, tuple[float, list[Finding]]] = {}
# Serializes the miss -> scan -> store sequence so concurrent cache misses don't
# each launch their own full scan (FastAPI runs sync endpoints in a threadpool).
_scan_lock = threading.Lock()


def _build_session() -> boto3.Session:
    profile = os.environ.get("CCG_AWS_PROFILE")
    assume_role = os.environ.get("CCG_ASSUME_ROLE_ARN")
    region = os.environ.get("CCG_AWS_REGION", "us-east-1")

    # region_name on the base session too, so CCG_AWS_REGION is honored on the
    # no-assume-role path (the production/ECS path), not just after assume-role.
    base = boto3.Session(profile_name=profile, region_name=region)
    if not assume_role:
        return base

    creds = base.client("sts").assume_role(RoleArn=assume_role, RoleSessionName="ccg-backend")[
        "Credentials"
    ]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )


def get_session() -> boto3.Session:
    """FastAPI dependency providing an authenticated boto3 Session to routes.

    Built per request (not cached) so assumed-role credentials can't go stale.
    Tests override this via ``app.dependency_overrides[get_session]`` so no unit
    test ever touches real AWS.
    """
    return _build_session()


def get_findings(session: Annotated[boto3.Session, Depends(get_session)]) -> list[Finding]:
    """Dependency: the findings from a full detective scan (cached briefly).

    A dependency that itself depends on another (get_session) — FastAPI resolves
    the chain. Routes that need the current posture (/findings, /compliance-score)
    depend on THIS, so the scan lives in one place and tests inject canned findings
    by overriding just this one function (no AWS, no monkeypatching internals).

    Serves a cached scan when one is fresh (< _SCAN_TTL_SECONDS), so a dashboard
    load doesn't fan out into several serial multi-region scans.
    """
    cached = _scan_cache.get("all")
    if cached is not None and time.monotonic() - cached[0] < _SCAN_TTL_SECONDS:
        return cached[1]

    with _scan_lock:
        # Re-check inside the lock: another thread may have scanned while we
        # waited, so we reuse its fresh result instead of scanning again.
        cached = _scan_cache.get("all")
        if cached is not None and time.monotonic() - cached[0] < _SCAN_TTL_SECONDS:
            return cached[1]
        findings = run_all_checks(session)
        # Timestamp AFTER the scan — a slow scan shouldn't be born already expired.
        _scan_cache["all"] = (time.monotonic(), findings)
        return findings
