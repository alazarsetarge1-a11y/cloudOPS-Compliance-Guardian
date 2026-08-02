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
from typing import Annotated

import boto3
from fastapi import Depends

from detective.checks.base import Finding
from detective.runner import run_all_checks


def _build_session() -> boto3.Session:
    profile = os.environ.get("CCG_AWS_PROFILE")
    assume_role = os.environ.get("CCG_ASSUME_ROLE_ARN")
    region = os.environ.get("CCG_AWS_REGION", "us-east-1")

    base = boto3.Session(profile_name=profile) if profile else boto3.Session()
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
    """Dependency: the findings from a full detective scan.

    A dependency that itself depends on another (get_session) — FastAPI resolves
    the chain. Routes that need the current posture (/findings, /compliance-score)
    depend on THIS, so the scan lives in one place and tests inject canned findings
    by overriding just this one function (no AWS, no monkeypatching internals).
    """
    return run_all_checks(session)
