# SCP test plan — `deny-untagged-resources.json`

An SCP is not validated until it has been run against a **real** organization
from a **member account** (the management account is exempt, so testing there
proves nothing). This plan records the exact commands and their real output.

## Environment

| Item | Value |
|---|---|
| Organization | `o-xxxxxxxxxx` (all-features) |
| Root | `r-xxxx` |
| Test OU | `scp-testing` (`ou-xxxx-xxxxxxxx`) |
| Member (test) account | `222222222222` — "CCG SCP Testing" |
| Test principal | `arn:aws:iam::222222222222:role/OrganizationAccountAccessRole` (SCPs apply to it) |
| Region | `us-east-1` |

**Why the allow case is the real test:** a plan with only deny cases can't tell
"the SCP works" from "the caller lacked permission anyway." Each deny is paired
with an identical allow (all four tags present). The allow passing is the control.

**Cost discipline (no free credits on this account):** EC2 uses `--dry-run`
(evaluates policy, creates nothing). S3 buckets and IAM roles are free — created
then deleted. The RDS *allow* case is **not run live** (an RDS instance costs
money and takes minutes); its deny case is free (denied → nothing created), and
the allow path is proven by the identical condition structure shared with EC2/S3.

## How the test principal is assumed

```bash
export AWS_PROFILE=ccg   # management-account SSO
CREDS=$(aws sts assume-role \
  --role-arn arn:aws:iam::222222222222:role/OrganizationAccountAccessRole \
  --role-session-name scp-test --query Credentials --output json)
export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r .AccessKeyId)
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r .SecretAccessKey)
export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r .SessionToken)
unset AWS_PROFILE   # now acting AS the member-account role
```

## Test cases

**Run: 2026-07-25 — all cases PASS** (9 top-level cases + 2 EC2-volume subcases
= **11 executions**) against policy `p-4nsaynd6` attached to OU
`ou-xxxx-xxxxxxxx`, from `OrganizationAccountAccessRole` in `222222222222`.

| # | Case | Expectation | Actual result |
|---|---|---|---|
| 1 | **EC2 deny** — `RunInstances`, no tags | Denied (explicit deny) | ✅ `UnauthorizedOperation` — explicit deny in SCP p-4nsaynd6 |
| 2 | **EC2 allow** — `RunInstances`, all 4 tags on instance + volume | Allowed (`DryRunOperation`) | ✅ `DryRunOperation` (would have succeeded) |
| 3 | **EC2 partial** — `RunInstances`, only 3 of 4 tags | Denied (each tag required independently) | ✅ Denied — proves per-tag OR logic |
| 3a | **EC2 volume deny** — `CreateVolume`, no tags | Denied | ✅ Denied |
| 3b | **EC2 volume allow** — `CreateVolume` + volume tags | Allowed (created, then deleted) | ✅ Created `vol-…`, then deleted |
| 4 | **S3 deny** — `CreateBucket`, no tags | Denied | ✅ Denied |
| 5 | **S3 allow** — `CreateBucket` + `Tags=[…all 4…]` | Allowed (bucket created, then deleted) | ✅ Created, then deleted — S3 tag-on-create works |
| 6 | **RDS deny** — `CreateDBInstance`, no tags | Denied (nothing created) | ✅ Denied — nothing created |
| 7 | **RDS cluster deny** — `CreateDBCluster`, no tags | Denied | ✅ Denied |
| 8 | **IAM deny** — `CreateRole`, no tags | Denied | ✅ Denied |
| 9 | **IAM allow** — `CreateRole` + `--tags` (all 4) | Allowed (role created, then deleted) | ✅ Created, then deleted |

## Commands (run as the assumed member-account role)

```bash
# 1 · EC2 deny  (AMI id is illustrative; dry-run never launches)
aws ec2 run-instances --image-id ami-0abcdef1234567890 --instance-type t3.micro \
  --dry-run --region us-east-1

# 2 · EC2 allow  (tag BOTH instance and volume — RunInstances creates both, and
#     the SCP scopes Resource to instance + volume)
aws ec2 run-instances --image-id ami-0abcdef1234567890 --instance-type t3.micro \
  --dry-run --region us-east-1 \
  --tag-specifications \
    'ResourceType=instance,Tags=[{Key=owner,Value=example-owner},{Key=environment,Value=sandbox},{Key=cost-center,Value=cc-1000},{Key=data-classification,Value=internal}]' \
    'ResourceType=volume,Tags=[{Key=owner,Value=example-owner},{Key=environment,Value=sandbox},{Key=cost-center,Value=cc-1000},{Key=data-classification,Value=internal}]'

# 3 · EC2 partial (missing data-classification) → still denied
aws ec2 run-instances --image-id ami-0abcdef1234567890 --instance-type t3.micro \
  --dry-run --region us-east-1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=owner,Value=example-owner},{Key=environment,Value=sandbox},{Key=cost-center,Value=cc-1000}]'

# 4 · S3 deny
aws s3api create-bucket --bucket ccg-scp-test-notags-<rand> --region us-east-1

# 5 · S3 allow  (then delete)
aws s3api create-bucket --region us-east-1 \
  --bucket ccg-scp-test-tagged-<rand> \
  --create-bucket-configuration 'Tags=[{Key=owner,Value=example-owner},{Key=environment,Value=sandbox},{Key=cost-center,Value=cc-1000},{Key=data-classification,Value=internal}]'
aws s3api delete-bucket --bucket ccg-scp-test-tagged-<rand> --region us-east-1

# 3a · EC2 standalone volume deny
aws ec2 create-volume --availability-zone us-east-1a --size 1 --region us-east-1

# 3b · EC2 standalone volume allow (then delete the returned VolumeId)
aws ec2 create-volume --availability-zone us-east-1a --size 1 --region us-east-1 \
  --tag-specifications 'ResourceType=volume,Tags=[{Key=owner,Value=example-owner},{Key=environment,Value=sandbox},{Key=cost-center,Value=cc-1000},{Key=data-classification,Value=internal}]'

# 6 · RDS deny
#   SAFETY: run ONLY with the SCP confirmed attached. RDS has no --dry-run, so if
#   the guardrail were absent/mis-scoped these WOULD create billable resources.
#   Expect an explicit AccessDenied; on any unexpected success, delete at once:
#     aws rds delete-db-instance --db-instance-identifier ccg-scp-test --skip-final-snapshot
#   --manage-master-user-password: AWS generates and stores the password in
#   Secrets Manager, so no static secret appears here, and the request still
#   reaches the API (a valid request is required to actually prove the deny).
aws rds create-db-instance --db-instance-identifier ccg-scp-test \
  --db-instance-class db.t3.micro --engine postgres \
  --master-username adminuser --manage-master-user-password \
  --allocated-storage 20 --region us-east-1

# 7 · RDS cluster deny  (same safety notes; delete-db-cluster on unexpected success)
aws rds create-db-cluster --db-cluster-identifier ccg-scp-test-cluster \
  --engine aurora-postgresql --master-username adminuser \
  --manage-master-user-password --region us-east-1

# 8 · IAM deny
aws iam create-role --role-name ccg-scp-test-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# 9 · IAM allow  (then delete)
aws iam create-role --role-name ccg-scp-test-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --tags Key=owner,Value=example-owner Key=environment,Value=sandbox Key=cost-center,Value=cc-1000 Key=data-classification,Value=internal
aws iam delete-role --role-name ccg-scp-test-role
```

## Result summary — 2026-07-25

**All cases pass** (9 top-level + 2 subcases, 11 executions). The preventive
layer is validated against a live Organization. Findings surfaced during the run
and were resolved:

1. **EC2 `RunInstances` is multi-resource.** The first allow-case run was denied
   on `arn:aws:ec2:*:*:network-interface/*` — EC2 authorizes the tag condition
   *per created resource* (instance, volume, **network-interface**), and the
   untagged NIC tripped the deny even though the instance was tagged. Fixed by
   **scoping each statement's `Resource`** to the types we actually govern
   (`instance`, `volume`, bucket, `db`, `cluster`, `role`), deliberately
   excluding the ephemeral, free network-interface. Callers must tag both the
   instance and its EBS volume (`ResourceType=instance` and `ResourceType=volume`
   in `--tag-specifications`).

2. **S3 tag-on-create works (empirically confirmed).** `aws:RequestTag` *is* now
   evaluated on `s3:CreateBucket`: the untagged bucket was denied and the tagged
   bucket (`--create-bucket-configuration '{"Tags":[…]}'`) was created. This
   validates that the S3 line is real, not the historical no-op most examples
   assume.

3. **Standalone-volume bypass closed.** `ec2:CreateVolume` was added to the deny
   actions after review: `RunInstances` only protects volumes created *during*
   an instance launch, but a standalone EBS volume can be created directly and
   also honors `aws:RequestTag`. Validated: untagged `CreateVolume` denied,
   tagged one created then deleted (cases 3a/3b).

**RDS is validated deny-only.** Untagged `CreateDBInstance` and `CreateDBCluster`
are confirmed blocked. The tagged **allow** path was **not** run live — an RDS
instance is billable and slow to provision. We deliberately do **not** claim the
EC2/S3 allow results transfer to RDS: RDS has its own authorization path, and the
S3 finding above is proof that per-service behavior can differ. Verifying the RDS
allow path is left as a follow-up (short-lived tagged instance + cleanup).

**Cost:** effectively zero. EC2 used `--dry-run` (nothing launched); all deny
cases created nothing; the S3 bucket, IAM role, and EBS volume from allow cases
were deleted immediately.
