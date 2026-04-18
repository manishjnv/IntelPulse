"""One-time AWS provisioning for the ECR-push + compose-pull deploy path.

Idempotent. Safe to re-run. All creations detect existing state and move on.

What it creates
---------------
1. ECR repositories (3):
     intelpulse/api, intelpulse/ui, intelpulse/worker
   (scheduler reuses the worker image — see docker-compose.yml)

2. GitHub OIDC identity provider in AWS IAM:
     arn:aws:iam::<acct>:oidc-provider/token.actions.githubusercontent.com
   (if one already exists, skip)

3. IAM role ``IntelPulseGitHubActionsECR`` trusted by that OIDC provider,
   scoped to the ``manishjnv/IntelPulse`` repo on ref ``refs/heads/main``.
   Attached inline policy grants ECR push/pull on the 3 repos only.

4. Inline policy ``ECRPullFromIntelPulseRepos`` attached to the EC2
   instance profile role (``BedrockAccessRole``) so ``docker compose pull``
   on the VPS can authenticate to ECR without static creds.

Prerequisites
-------------
- Local AWS creds with IAM + ECR admin on account 604275788592.
- boto3 installed (``pip install boto3``).

Usage
-----
    python scripts/provision_ecr.py

Environment overrides
---------------------
    AWS_REGION              default us-east-1
    GITHUB_REPO             default manishjnv/IntelPulse
    GITHUB_REF              default refs/heads/main
    EC2_INSTANCE_ROLE_NAME  default BedrockAccessRole

Leaves resources untouched if already present; logs what it found.

Deletion / rollback
-------------------
Nothing destructive. To tear down, follow the AWS console:
  1. Detach inline policy ``ECRPullFromIntelPulseRepos`` from
     ``BedrockAccessRole``.
  2. Delete role ``IntelPulseGitHubActionsECR``.
  3. Delete the OIDC provider (only if nothing else in the account uses it).
  4. Delete the 3 ECR repositories (empty first).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "manishjnv/IntelPulse")
GITHUB_REF = os.environ.get("GITHUB_REF", "refs/heads/main")
EC2_ROLE_NAME = os.environ.get("EC2_INSTANCE_ROLE_NAME", "BedrockAccessRole")

GHA_ROLE_NAME = "IntelPulseGitHubActionsECR"
EC2_POLICY_NAME = "ECRPullFromIntelPulseRepos"
OIDC_PROVIDER_URL = "token.actions.githubusercontent.com"
# GitHub's published OIDC thumbprint; AWS now auto-resolves TLS for the
# well-known providers, so the thumbprint list can be empty — but older
# regions/accounts still require at least one. Keep the current value here.
OIDC_THUMBPRINTS = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

REPOS = ["intelpulse/api", "intelpulse/ui", "intelpulse/worker"]

iam = boto3.client("iam")
ecr = boto3.client("ecr", region_name=REGION)
sts = boto3.client("sts")


def _account_id() -> str:
    return sts.get_caller_identity()["Account"]


def ensure_repos() -> list[str]:
    uris: list[str] = []
    acct = _account_id()
    for name in REPOS:
        try:
            r = ecr.describe_repositories(repositoryNames=[name])
            uri = r["repositories"][0]["repositoryUri"]
            print(f"  ECR repo exists: {uri}")
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "RepositoryNotFoundException":
                raise
            r = ecr.create_repository(
                repositoryName=name,
                imageScanningConfiguration={"scanOnPush": True},
                imageTagMutability="MUTABLE",
                encryptionConfiguration={"encryptionType": "AES256"},
            )
            uri = r["repository"]["repositoryUri"]
            print(f"  ECR repo CREATED: {uri}")
        uris.append(uri)

        # Lifecycle policy: expire untagged images > 7 days, keep last 20 tagged.
        lifecycle = {
            "rules": [
                {
                    "rulePriority": 1,
                    "description": "Expire untagged images after 7 days",
                    "selection": {
                        "tagStatus": "untagged",
                        "countType": "sinceImagePushed",
                        "countUnit": "days",
                        "countNumber": 7,
                    },
                    "action": {"type": "expire"},
                },
                {
                    "rulePriority": 2,
                    "description": "Keep the last 20 tagged images",
                    "selection": {
                        "tagStatus": "any",
                        "countType": "imageCountMoreThan",
                        "countNumber": 20,
                    },
                    "action": {"type": "expire"},
                },
            ]
        }
        ecr.put_lifecycle_policy(
            repositoryName=name, lifecyclePolicyText=json.dumps(lifecycle)
        )
    return uris


def ensure_oidc_provider() -> str:
    acct = _account_id()
    target_arn = f"arn:aws:iam::{acct}:oidc-provider/{OIDC_PROVIDER_URL}"
    try:
        iam.get_open_id_connect_provider(OpenIDConnectProviderArn=target_arn)
        print(f"  OIDC provider exists: {target_arn}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "NoSuchEntity":
            raise
        iam.create_open_id_connect_provider(
            Url=f"https://{OIDC_PROVIDER_URL}",
            ClientIDList=["sts.amazonaws.com"],
            ThumbprintList=OIDC_THUMBPRINTS,
        )
        print(f"  OIDC provider CREATED: {target_arn}")
    return target_arn


def ensure_gha_role(oidc_arn: str, repo_uris: list[str]) -> str:
    acct = _account_id()
    # GitHub OIDC sub claim shape depends on the workflow context:
    #   - plain ref runs:          repo:<owner>/<repo>:ref:refs/heads/<branch>
    #   - workflows with an
    #     `environment:` job key:  repo:<owner>/<repo>:environment:<env>
    # ecr-push.yml declares `environment: production`, so its sub is the
    # second shape. Allow both so we don't have to remember which context
    # a given workflow uses.
    allowed_subs = [
        f"repo:{GITHUB_REPO}:ref:{GITHUB_REF}",
        f"repo:{GITHUB_REPO}:environment:production",
    ]
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Federated": oidc_arn},
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{OIDC_PROVIDER_URL}:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        f"{OIDC_PROVIDER_URL}:sub": allowed_subs,
                    },
                },
            }
        ],
    }
    try:
        iam.get_role(RoleName=GHA_ROLE_NAME)
        iam.update_assume_role_policy(
            RoleName=GHA_ROLE_NAME, PolicyDocument=json.dumps(trust)
        )
        print(f"  IAM role exists (trust policy refreshed): {GHA_ROLE_NAME}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "NoSuchEntity":
            raise
        iam.create_role(
            RoleName=GHA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust),
            Description=(
                "GitHub Actions OIDC role for pushing IntelPulse images to ECR. "
                "Scoped to repo/main only."
            ),
            MaxSessionDuration=3600,
        )
        print(f"  IAM role CREATED: {GHA_ROLE_NAME}")

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ECRAuth",
                "Effect": "Allow",
                "Action": "ecr:GetAuthorizationToken",
                "Resource": "*",
            },
            {
                "Sid": "ECRPushPull",
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:BatchGetImage",
                    "ecr:CompleteLayerUpload",
                    "ecr:DescribeImages",
                    "ecr:DescribeRepositories",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:InitiateLayerUpload",
                    "ecr:PutImage",
                    "ecr:UploadLayerPart",
                ],
                "Resource": [
                    f"arn:aws:ecr:{REGION}:{acct}:repository/{name}"
                    for name in REPOS
                ],
            },
        ],
    }
    iam.put_role_policy(
        RoleName=GHA_ROLE_NAME,
        PolicyName="ECRPushIntelPulse",
        PolicyDocument=json.dumps(policy),
    )
    print("  inline policy ECRPushIntelPulse attached")
    return f"arn:aws:iam::{acct}:role/{GHA_ROLE_NAME}"


def ensure_ec2_ecr_pull() -> None:
    """Attach an ECR pull inline policy to the EC2 instance profile role."""
    acct = _account_id()
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ECRAuth",
                "Effect": "Allow",
                "Action": "ecr:GetAuthorizationToken",
                "Resource": "*",
            },
            {
                "Sid": "ECRPullOnly",
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:BatchGetImage",
                    "ecr:DescribeImages",
                    "ecr:DescribeRepositories",
                    "ecr:GetDownloadUrlForLayer",
                ],
                "Resource": [
                    f"arn:aws:ecr:{REGION}:{acct}:repository/{name}"
                    for name in REPOS
                ],
            },
        ],
    }
    try:
        iam.put_role_policy(
            RoleName=EC2_ROLE_NAME,
            PolicyName=EC2_POLICY_NAME,
            PolicyDocument=json.dumps(policy),
        )
        print(
            f"  attached inline policy {EC2_POLICY_NAME!r} to {EC2_ROLE_NAME!r}"
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchEntity":
            print(
                f"  WARNING: EC2 role {EC2_ROLE_NAME!r} not found. Skipping."
                " Attach the policy manually once the role exists."
            )
            return
        raise


def main() -> int:
    print(f"AWS account: {_account_id()}")
    print(f"Region: {REGION}")
    print()
    print("== ECR repositories ==")
    repo_uris = ensure_repos()
    print()
    print("== GitHub Actions OIDC provider ==")
    oidc_arn = ensure_oidc_provider()
    print()
    print("== IAM role for GitHub Actions ==")
    role_arn = ensure_gha_role(oidc_arn, repo_uris)
    print()
    print("== EC2 instance profile ECR pull ==")
    ensure_ec2_ecr_pull()
    print()
    print("== summary ==")
    print(json.dumps(
        {
            "ecr_repos": repo_uris,
            "oidc_provider": oidc_arn,
            "github_actions_role": role_arn,
            "ec2_role_patched": EC2_ROLE_NAME,
        },
        indent=2,
    ))
    print()
    print("Next steps:")
    print(
        "  1. Copy the `github_actions_role` ARN above into the GH secret "
        "`AWS_ROLE_ECR_PUSH` (repo or environment-scoped)."
    )
    print("  2. Merge the .github/workflows/ecr-push.yml workflow to start")
    print("     pushing images to ECR on every push to main.")
    print(
        "  3. Once at least one successful push exists, flip the SSH deploy"
        " step from scripts/deploy.sh to scripts/deploy-ecr.sh."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
