"""Idempotent provisioning for the IntelPulse VirusTotal Bedrock action group.

Creates or updates, in order:
  1. IAM role ``intelpulse-virustotal-lookup-role`` (Lambda trust + CloudWatch + Secrets Manager read)
  2. Secrets Manager secret ``intelpulse/virustotal`` (empty by default → Lambda stub-falls-back)
  3. CloudWatch log group ``/aws/lambda/intelpulse-virustotal-lookup`` (14-day retention)
  4. Lambda function ``intelpulse-virustotal-lookup`` (Python 3.12, handler.lambda_handler)
  5. Lambda resource policy granting ``bedrock.amazonaws.com`` invoke rights
  6. Bedrock agent action group ``virustotal_lookup`` on the IOC-Analyst agent
  7. ``prepare_agent`` on IOC-Analyst
  8. Bumps the ``live`` alias to a new numbered version that includes the action group

Re-runnable; every step detects existing state and updates in place.

Usage
-----
    python -m infra.scripts.provision_bedrock_action_group

Optional env vars
-----------------
    VIRUSTOTAL_API_KEY   Real API key; if set, overwrites the secret and disables stub mode
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
ACCOUNT_ID = "604275788592"
ROLE_NAME = "intelpulse-virustotal-lookup-role"
SECRET_NAME = "intelpulse/virustotal"
FUNCTION_NAME = "intelpulse-virustotal-lookup"
LOG_GROUP = f"/aws/lambda/{FUNCTION_NAME}"

IOC_ANALYST_ID = "UX0RYONP98"
IOC_ANALYST_ALIAS_ID = "SFDO1GO27Y"   # "live"
ACTION_GROUP_NAME = "virustotal_lookup"

LAMBDA_DIR = Path(__file__).resolve().parent.parent / "lambdas" / "virustotal_lookup"

iam = boto3.client("iam")
secrets = boto3.client("secretsmanager", region_name=REGION)
logs = boto3.client("logs", region_name=REGION)
lmb = boto3.client("lambda", region_name=REGION)
ba = boto3.client("bedrock-agent", region_name=REGION)


def step(n: int, desc: str) -> None:
    print(f"\n=== [{n}] {desc} ===", flush=True)


# ────────────────────────────────────────────────────────────────────────
# 1. IAM role
# ────────────────────────────────────────────────────────────────────────
def ensure_role() -> str:
    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    }
    try:
        r = iam.get_role(RoleName=ROLE_NAME)
        print(f"role exists: {r['Role']['Arn']}")
    except iam.exceptions.NoSuchEntityException:
        r = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust),
            Description="Execution role for IntelPulse VirusTotal Lambda action group",
            Tags=[{"Key": "Project", "Value": "IntelPulse"},
                  {"Key": "Component", "Value": "bedrock-action-group"}],
        )
        print(f"role created: {r['Role']['Arn']}")

    attached = iam.list_attached_role_policies(RoleName=ROLE_NAME)["AttachedPolicies"]
    if not any(p["PolicyName"] == "AWSLambdaBasicExecutionRole" for p in attached):
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        print("attached AWSLambdaBasicExecutionRole")

    return r["Role"]["Arn"]


# ────────────────────────────────────────────────────────────────────────
# 2. Secrets Manager
# ────────────────────────────────────────────────────────────────────────
def ensure_secret() -> str:
    real_key = os.environ.get("VIRUSTOTAL_API_KEY", "").strip()
    payload = json.dumps({"VIRUSTOTAL_API_KEY": real_key})

    try:
        s = secrets.describe_secret(SecretId=SECRET_NAME)
        arn = s["ARN"]
        print(f"secret exists: {arn}")
        if real_key:
            secrets.put_secret_value(SecretId=SECRET_NAME, SecretString=payload)
            print("secret value UPDATED from VIRUSTOTAL_API_KEY env var")
        return arn
    except secrets.exceptions.ResourceNotFoundException:
        r = secrets.create_secret(
            Name=SECRET_NAME,
            Description=("VirusTotal API key for IntelPulse. Leave empty to run in "
                         "stub mode; set VIRUSTOTAL_API_KEY for real data."),
            SecretString=payload,
            Tags=[{"Key": "Project", "Value": "IntelPulse"}],
        )
        print(f"secret created: {r['ARN']}")
        return r["ARN"]


# ────────────────────────────────────────────────────────────────────────
# 3. Inline policy for Secrets Manager read
# ────────────────────────────────────────────────────────────────────────
def ensure_inline_policy(secret_arn: str) -> None:
    # Secrets Manager ARN pattern has a 6-char random suffix; allow both exact + wildcard
    # suffix to survive rotation.
    bare_arn = secret_arn.rsplit("-", 1)[0] if "-" in secret_arn.split(":")[-1] else secret_arn
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": [secret_arn, f"{bare_arn}-*"],
        }],
    }
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="SecretsManagerRead",
        PolicyDocument=json.dumps(policy),
    )
    print("inline policy SecretsManagerRead applied")


# ────────────────────────────────────────────────────────────────────────
# 4. CloudWatch log group
# ────────────────────────────────────────────────────────────────────────
def ensure_log_group() -> None:
    try:
        logs.create_log_group(logGroupName=LOG_GROUP)
        print(f"log group created: {LOG_GROUP}")
    except logs.exceptions.ResourceAlreadyExistsException:
        print(f"log group exists: {LOG_GROUP}")
    logs.put_retention_policy(logGroupName=LOG_GROUP, retentionInDays=14)


# ────────────────────────────────────────────────────────────────────────
# 5. Lambda
# ────────────────────────────────────────────────────────────────────────
def _zip_handler() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(LAMBDA_DIR / "handler.py", arcname="handler.py")
    return buf.getvalue()


def ensure_lambda(role_arn: str, secret_arn: str) -> str:
    zip_bytes = _zip_handler()

    try:
        cfg = lmb.get_function(FunctionName=FUNCTION_NAME)["Configuration"]
        print(f"lambda exists: {cfg['FunctionArn']}")

        lmb.update_function_code(FunctionName=FUNCTION_NAME, ZipFile=zip_bytes)
        lmb.get_waiter("function_updated").wait(FunctionName=FUNCTION_NAME)

        lmb.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Role=role_arn,
            Handler="handler.lambda_handler",
            Runtime="python3.12",
            Timeout=30,
            MemorySize=256,
            Environment={"Variables": {"SECRET_ARN": secret_arn}},
        )
        lmb.get_waiter("function_updated").wait(FunctionName=FUNCTION_NAME)
        return cfg["FunctionArn"]

    except lmb.exceptions.ResourceNotFoundException:
        pass

    print("waiting 12s for IAM role propagation before first create…")
    time.sleep(12)

    r = lmb.create_function(
        FunctionName=FUNCTION_NAME,
        Runtime="python3.12",
        Role=role_arn,
        Handler="handler.lambda_handler",
        Code={"ZipFile": zip_bytes},
        Description=("IntelPulse VirusTotal lookup — supports legacy direct and Bedrock "
                     "action-group shapes; stub-falls-back when no API key is set."),
        Timeout=30,
        MemorySize=256,
        Environment={"Variables": {"SECRET_ARN": secret_arn}},
        Tags={"Project": "IntelPulse", "Component": "bedrock-action-group"},
    )
    print(f"lambda created: {r['FunctionArn']}")
    lmb.get_waiter("function_active_v2").wait(FunctionName=FUNCTION_NAME)
    return r["FunctionArn"]


# ────────────────────────────────────────────────────────────────────────
# 6. Lambda resource policy (Bedrock invoke)
# ────────────────────────────────────────────────────────────────────────
def ensure_bedrock_invoke_perm() -> None:
    sid = "AllowBedrockInvoke"
    try:
        existing = lmb.get_policy(FunctionName=FUNCTION_NAME)["Policy"]
        if f'"Sid":"{sid}"' in existing.replace(" ", "") or f'"Sid": "{sid}"' in existing:
            print(f"bedrock invoke permission already present (sid={sid})")
            return
    except lmb.exceptions.ResourceNotFoundException:
        pass  # no policy yet

    lmb.add_permission(
        FunctionName=FUNCTION_NAME,
        StatementId=sid,
        Action="lambda:InvokeFunction",
        Principal="bedrock.amazonaws.com",
        SourceArn=f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent/{IOC_ANALYST_ID}",
    )
    print(f"bedrock invoke permission added (sid={sid})")


# ────────────────────────────────────────────────────────────────────────
# 7. Bedrock agent action group
# ────────────────────────────────────────────────────────────────────────
_FUNCTION_SCHEMA = {
    "functions": [{
        "name": "lookup_ioc",
        "description": (
            "Query VirusTotal for reputation data on an indicator of compromise. "
            "Returns malicious/suspicious/harmless detection counts, plus contextual "
            "metadata like country-of-origin (for IPs), categorization (for domains), "
            "or file metadata (for hashes)."
        ),
        "parameters": {
            "ioc": {
                "type": "string",
                "description": "The indicator to look up — IP address, domain, or file hash.",
                "required": True,
            },
            "ioc_type": {
                "type": "string",
                "description": "One of 'ip', 'domain', 'hash'. Use 'hash' for md5/sha1/sha256.",
                "required": True,
            },
        },
        "requireConfirmation": "DISABLED",
    }]
}


def ensure_action_group(function_arn: str) -> None:
    existing_id: str | None = None
    r = ba.list_agent_action_groups(
        agentId=IOC_ANALYST_ID, agentVersion="DRAFT", maxResults=25
    )
    for ag in r.get("actionGroupSummaries", []):
        if ag["actionGroupName"] == ACTION_GROUP_NAME:
            existing_id = ag["actionGroupId"]
            break

    if existing_id:
        print(f"action group exists: {existing_id}; updating")
        ba.update_agent_action_group(
            agentId=IOC_ANALYST_ID,
            agentVersion="DRAFT",
            actionGroupId=existing_id,
            actionGroupName=ACTION_GROUP_NAME,
            description="VirusTotal IOC reputation lookup via Lambda",
            actionGroupExecutor={"lambda": function_arn},
            functionSchema=_FUNCTION_SCHEMA,
            actionGroupState="ENABLED",
        )
        return

    r = ba.create_agent_action_group(
        agentId=IOC_ANALYST_ID,
        agentVersion="DRAFT",
        actionGroupName=ACTION_GROUP_NAME,
        description="VirusTotal IOC reputation lookup via Lambda",
        actionGroupExecutor={"lambda": function_arn},
        functionSchema=_FUNCTION_SCHEMA,
        actionGroupState="ENABLED",
    )
    print(f"action group created: {r['agentActionGroup']['actionGroupId']}")


# ────────────────────────────────────────────────────────────────────────
# 8. Prepare agent + bump alias
# ────────────────────────────────────────────────────────────────────────
def prepare_and_bump_alias() -> None:
    print("prepare_agent on IOC-Analyst…")
    ba.prepare_agent(agentId=IOC_ANALYST_ID)

    # Wait until PREPARED
    for _ in range(40):
        a = ba.get_agent(agentId=IOC_ANALYST_ID)["agent"]
        status = a["agentStatus"]
        if status == "PREPARED":
            print("agent status: PREPARED")
            break
        if status == "FAILED":
            raise RuntimeError(f"agent prepare FAILED: {a.get('failureReasons')}")
        time.sleep(3)
    else:
        raise RuntimeError("agent did not reach PREPARED within 120s")

    # Bump the `live` alias. Strategy: create a temp alias with no routingConfiguration
    # (Bedrock auto-creates a new numbered version from DRAFT), extract that version
    # number, then update the `live` alias to point at it. Finally delete the temp alias.
    temp_name = f"autobump-{int(time.time())}"
    temp = ba.create_agent_alias(
        agentId=IOC_ANALYST_ID,
        agentAliasName=temp_name,
        description="Transient alias to extract newest version number; safe to delete.",
    )
    temp_alias_id = temp["agentAlias"]["agentAliasId"]
    print(f"temp alias {temp_alias_id} created (status={temp['agentAlias']['agentAliasStatus']})")

    # Wait for temp alias PREPARED — routingConfiguration[].agentVersion is only
    # populated once the new numbered version has been cut + prepared.
    prepared_alias = None
    for _ in range(40):
        s = ba.get_agent_alias(agentId=IOC_ANALYST_ID, agentAliasId=temp_alias_id)
        status = s["agentAlias"]["agentAliasStatus"]
        if status == "PREPARED":
            prepared_alias = s["agentAlias"]
            break
        if status == "FAILED":
            raise RuntimeError(f"temp alias failed: {s['agentAlias']}")
        time.sleep(3)
    else:
        raise RuntimeError("temp alias did not reach PREPARED within 120s")

    routing = prepared_alias.get("routingConfiguration") or []
    if not routing or "agentVersion" not in routing[0]:
        # Fallback: enumerate agent versions and pick the max numeric one
        versions = ba.list_agent_versions(agentId=IOC_ANALYST_ID, maxResults=50).get(
            "agentVersionSummaries", []
        )
        numeric = sorted(
            [v["agentVersion"] for v in versions if v["agentVersion"].isdigit()],
            key=int,
        )
        if not numeric:
            raise RuntimeError(
                f"no numbered agent version found; routing was {routing}, versions={versions}"
            )
        new_version = numeric[-1]
        print(f"(fallback) picked newest numeric version: {new_version}")
    else:
        new_version = routing[0]["agentVersion"]
        print(f"new version from temp alias: {new_version}")

    # Now update `live` to point at the new version
    ba.update_agent_alias(
        agentId=IOC_ANALYST_ID,
        agentAliasId=IOC_ANALYST_ALIAS_ID,
        agentAliasName="live",
        routingConfiguration=[{"agentVersion": new_version}],
    )
    print(f"alias 'live' ({IOC_ANALYST_ALIAS_ID}) bumped to version {new_version}")

    # Clean up temp alias
    try:
        ba.delete_agent_alias(agentId=IOC_ANALYST_ID, agentAliasId=temp_alias_id)
        print(f"temp alias {temp_alias_id} deleted")
    except ClientError as e:
        print(f"(non-fatal) could not delete temp alias: {e}")


# ────────────────────────────────────────────────────────────────────────
# main
# ────────────────────────────────────────────────────────────────────────
def main() -> int:
    step(1, "IAM role")
    role_arn = ensure_role()

    step(2, "Secrets Manager")
    secret_arn = ensure_secret()

    step(3, "Inline policy (Secrets Manager read)")
    ensure_inline_policy(secret_arn)

    step(4, "CloudWatch log group")
    ensure_log_group()

    step(5, "Lambda function")
    function_arn = ensure_lambda(role_arn, secret_arn)

    step(6, "Lambda resource policy (Bedrock invoke)")
    ensure_bedrock_invoke_perm()

    step(7, "Bedrock agent action group")
    ensure_action_group(function_arn)

    step(8, "Prepare agent + bump live alias")
    prepare_and_bump_alias()

    print()
    print("DONE - all resources provisioned.")
    print(f"  Lambda ARN:  {function_arn}")
    print(f"  Secret ARN:  {secret_arn}")
    print(f"  Agent:       IntelPulse-IOC-Analyst ({IOC_ANALYST_ID})")
    print(f"  Alias:       live ({IOC_ANALYST_ALIAS_ID})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
