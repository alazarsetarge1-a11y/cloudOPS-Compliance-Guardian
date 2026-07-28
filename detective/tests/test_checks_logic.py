"""Unit tests for the pure evaluation logic of the regional checks.

Security groups, RDS encryption, and tag compliance all keep their decision logic
in pure helpers that take plain dicts (the shape AWS returns) and return a
Finding — so these tests need no AWS, no Stubber, just literals.
"""

from detective.checks import rds_encryption, security_groups, tag_compliance
from detective.checks.base import Status

ACCOUNT = "123456789012"
REGION = "us-east-1"


# --- security groups ---------------------------------------------------------


def test_sg_ssh_open_to_world_is_noncompliant():
    sg = {
        "GroupId": "sg-1",
        "IpPermissions": [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ],
    }
    f = security_groups._evaluate_sg(ACCOUNT, REGION, sg)
    assert f.status == Status.NON_COMPLIANT
    assert "tcp/22" in f.evidence["world_open"]


def test_sg_all_traffic_open_is_flagged():
    sg = {
        "GroupId": "sg-2",
        "IpPermissions": [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
    }
    f = security_groups._evaluate_sg(ACCOUNT, REGION, sg)
    assert f.status == Status.NON_COMPLIANT
    assert "ALL traffic" in f.evidence["world_open"]


def test_sg_ssh_open_only_to_known_cidr_is_compliant():
    sg = {
        "GroupId": "sg-3",
        "IpPermissions": [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "10.0.0.0/8"}],  # internal only
            }
        ],
    }
    f = security_groups._evaluate_sg(ACCOUNT, REGION, sg)
    assert f.status == Status.COMPLIANT


def test_sg_wide_port_range_covering_ssh_is_flagged():
    sg = {
        "GroupId": "sg-4",
        "IpPermissions": [
            {
                "IpProtocol": "tcp",
                "FromPort": 0,
                "ToPort": 1024,  # range spans 22
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ],
    }
    f = security_groups._evaluate_sg(ACCOUNT, REGION, sg)
    assert f.status == Status.NON_COMPLIANT


# --- rds encryption ----------------------------------------------------------


def test_rds_unencrypted_is_noncompliant():
    db = {"DBInstanceIdentifier": "db1", "StorageEncrypted": False}
    f = rds_encryption._evaluate_db(ACCOUNT, REGION, db)
    assert f.status == Status.NON_COMPLIANT
    assert f.evidence["storage_encrypted"] is False


def test_rds_encrypted_is_compliant():
    db = {"DBInstanceIdentifier": "db2", "StorageEncrypted": True}
    f = rds_encryption._evaluate_db(ACCOUNT, REGION, db)
    assert f.status == Status.COMPLIANT


# --- tag compliance ----------------------------------------------------------


def test_tags_all_present_is_compliant():
    resource = {
        "ResourceARN": "arn:aws:s3:::my-bucket",
        "Tags": [
            {"Key": "owner", "Value": "alazar"},
            {"Key": "environment", "Value": "sandbox"},
            {"Key": "cost-center", "Value": "cc-1000"},
            {"Key": "data-classification", "Value": "internal"},
        ],
    }
    f = tag_compliance._evaluate_resource(ACCOUNT, REGION, resource)
    assert f.status == Status.COMPLIANT


def test_tags_missing_some_is_noncompliant():
    resource = {
        "ResourceARN": "arn:aws:s3:::my-bucket",
        "Tags": [{"Key": "owner", "Value": "alazar"}],
    }
    f = tag_compliance._evaluate_resource(ACCOUNT, REGION, resource)
    assert f.status == Status.NON_COMPLIANT
    assert set(f.evidence["missing_tags"]) == {"environment", "cost-center", "data-classification"}
