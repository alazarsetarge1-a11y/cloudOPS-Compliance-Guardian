"""Unit tests for the s3-public-access check.

No AWS account, no network — botocore's Stubber feeds canned API responses to a
real S3 client, and we assert on the Finding the check returns. This is the
concrete payoff of keeping checks as pure functions: every branch is testable
in milliseconds, offline, and deterministically.

We test the `_evaluate_bucket` helper directly (it takes the client as an arg),
which keeps the tests focused on the compliance logic without the STS call that
`run()` makes to resolve the account id.
"""

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from detective.checks import s3_public_access as chk
from detective.checks.base import Status

ACCOUNT = "123456789012"


def _s3_client():
    # Dummy creds/region — Stubber intercepts before any real call goes out.
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )


def test_full_bpa_is_compliant():
    s3 = _s3_client()
    with Stubber(s3) as stub:
        stub.add_response(
            "get_public_access_block",
            {"PublicAccessBlockConfiguration": dict.fromkeys(chk._BPA_FLAGS, True)},
            {"Bucket": "locked-bucket"},
        )
        finding = chk._evaluate_bucket(s3, ACCOUNT, "locked-bucket")
    assert finding.status == Status.COMPLIANT
    assert finding.resource_arn == "arn:aws:s3:::locked-bucket"


def test_missing_bpa_is_noncompliant():
    s3 = _s3_client()
    with Stubber(s3) as stub:
        stub.add_client_error(
            "get_public_access_block",
            service_error_code="NoSuchPublicAccessBlockConfiguration",
            expected_params={"Bucket": "bare-bucket"},
        )
        finding = chk._evaluate_bucket(s3, ACCOUNT, "bare-bucket")
    assert finding.status == Status.NON_COMPLIANT
    assert finding.evidence["block_public_access"] is None


def test_partial_bpa_is_noncompliant():
    s3 = _s3_client()
    cfg = dict.fromkeys(chk._BPA_FLAGS, True)
    cfg["BlockPublicPolicy"] = False  # one flag off → still exposable
    with Stubber(s3) as stub:
        stub.add_response(
            "get_public_access_block",
            {"PublicAccessBlockConfiguration": cfg},
            {"Bucket": "partial-bucket"},
        )
        finding = chk._evaluate_bucket(s3, ACCOUNT, "partial-bucket")
    assert finding.status == Status.NON_COMPLIANT
    assert finding.evidence["BlockPublicPolicy"] is False


def test_access_denied_is_error_not_compliant():
    s3 = _s3_client()
    with Stubber(s3) as stub:
        stub.add_client_error(
            "get_public_access_block",
            service_error_code="AccessDenied",
            expected_params={"Bucket": "opaque-bucket"},
        )
        finding = chk._evaluate_bucket(s3, ACCOUNT, "opaque-bucket")
    # The whole point: a check that can't SEE the resource must not call it clean.
    assert finding.status == Status.ERROR


def test_unknown_error_is_raised_not_swallowed():
    s3 = _s3_client()
    with Stubber(s3) as stub:
        stub.add_client_error(
            "get_public_access_block",
            service_error_code="InternalError",
            expected_params={"Bucket": "flaky-bucket"},
        )
        # An unknown error must propagate as ClientError, not become a false pass.
        with pytest.raises(ClientError):
            chk._evaluate_bucket(s3, ACCOUNT, "flaky-bucket")
