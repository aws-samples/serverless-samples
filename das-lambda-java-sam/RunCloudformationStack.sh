#!/bin/bash
# Deploy / update the parent CloudFormation stack for the DAS Lambda Java SAM
# solution. Idempotent — safe to re-run.
#
# Usage:
#   sh ./RunCloudformationStack.sh <AWS_PROFILE> <STACK_NAME>
#
# Optional environment variables:
#   DAS_GITHUB_LOCATION
#       Public Git URL the EC2 UserData clones from. Default: upstream
#       aws-samples. Set to point at a fork during pre-PR testing.
#   DAS_LAMBDA_CODE_S3_URI
#       s3://bucket/key.tgz of an already-uploaded code archive.
#   DAS_LAMBDA_CODE_LOCAL_DIR
#       Local directory containing das-lambda-java-sam/. The script will tar
#       it up and upload to s3://${CFT_BUCKET}/das-code.tgz, then point the
#       CFN parameter DASLambdaCodeS3Uri at that URI.
#   CFT_BUCKET
#       Reuse an existing CFT packaging bucket (e.g. on retry after a failed
#       deploy). When unset, the script creates a fresh randomized bucket.

set -euo pipefail

# ---------- Argument validation ----------
if [ $# -lt 2 ]; then
    echo "Usage: sh $0 <AWS_PROFILE> <STACK_NAME>"
    exit 1
fi

AWS_USER="$1"
STACK_NAME="$2"

# ---------- Credential and region validation ----------
echo "Verifying AWS credentials for profile '$AWS_USER'..."
if ! aws sts get-caller-identity --profile "$AWS_USER" --no-cli-pager > /dev/null 2>&1; then
    echo "ERROR: Cannot authenticate with profile '$AWS_USER'."
    echo "Run: aws sts get-caller-identity --profile $AWS_USER"
    exit 1
fi
AWS_ACCOUNT_NUMBER=$(aws sts get-caller-identity --profile "$AWS_USER" \
    --query 'Account' --output text --no-cli-pager)
echo "  ✓ Authenticated to account $AWS_ACCOUNT_NUMBER"

AWS_REGION=$(aws configure get region --profile "$AWS_USER" 2>/dev/null || echo "")
if [ -z "$AWS_REGION" ]; then
    echo "ERROR: No region configured for profile '$AWS_USER'."
    echo "Run: aws configure set region <region> --profile $AWS_USER"
    exit 1
fi
echo "  ✓ Region: $AWS_REGION"
echo ""

# ---------- CFT packaging bucket: reuse if env var set, else create ----------
if [ -n "${CFT_BUCKET:-}" ]; then
    echo "Reusing existing CFT bucket: $CFT_BUCKET"
    if ! aws s3api head-bucket --bucket "$CFT_BUCKET" --profile "$AWS_USER" 2>/dev/null; then
        echo "ERROR: Bucket '$CFT_BUCKET' is not accessible. Unset CFT_BUCKET to create a new one."
        exit 1
    fi
else
    # POSIX-portable unique suffix. $RANDOM is a bash-ism (empty under dash/sh
    # on Linux), which would produce a non-unique 'cft-bucket-<acct>-' name.
    # Use epoch seconds + PID, which is unique enough for per-run bucket names
    # and works in any POSIX shell.
    random_number="$(date +%s)$$"
    CFT_BUCKET="cft-bucket-${AWS_ACCOUNT_NUMBER}-${random_number}"
    echo "Creating CFT bucket: s3://${CFT_BUCKET}"
    aws s3 mb "s3://${CFT_BUCKET}" --profile "$AWS_USER" --no-cli-pager
    sleep 30
fi
echo ""

# ---------- CloudFront managed prefix list lookup ----------
echo "Looking up CloudFront managed prefix list ID for region $AWS_REGION..."
CF_PREFIX_LIST_ID=$(aws ec2 describe-managed-prefix-lists \
    --filters "Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing" \
    --query "PrefixLists[0].PrefixListId" --output text \
    --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager)
if [ -z "$CF_PREFIX_LIST_ID" ] || [ "$CF_PREFIX_LIST_ID" = "None" ]; then
    echo "ERROR: Could not find CloudFront managed prefix list in region $AWS_REGION"
    exit 1
fi
echo "  ✓ Prefix list: $CF_PREFIX_LIST_ID"
echo ""

# ---------- Code-source override (dev only) ----------
DAS_GITHUB_LOCATION="${DAS_GITHUB_LOCATION:-}"
DAS_LAMBDA_CODE_S3_URI="${DAS_LAMBDA_CODE_S3_URI:-}"
DAS_LAMBDA_CODE_LOCAL_DIR="${DAS_LAMBDA_CODE_LOCAL_DIR:-}"

if [ -z "$DAS_LAMBDA_CODE_S3_URI" ] && [ -n "$DAS_LAMBDA_CODE_LOCAL_DIR" ]; then
    if [ ! -d "$DAS_LAMBDA_CODE_LOCAL_DIR/das-lambda-java-sam" ]; then
        echo "ERROR: DAS_LAMBDA_CODE_LOCAL_DIR ($DAS_LAMBDA_CODE_LOCAL_DIR) must contain a 'das-lambda-java-sam/' subdirectory"
        exit 1
    fi
    echo "Packaging local code from $DAS_LAMBDA_CODE_LOCAL_DIR..."
    echo "  (this can take 30-60s on slow connections — archive is uploaded to s3://${CFT_BUCKET}/das-code.tgz)"
    TARBALL=$(mktemp -t das-code-XXXXXX.tgz)
    # COPYFILE_DISABLE=1 prevents macOS from emitting AppleDouble (._*) sidecar
    # metadata files into the archive.
    COPYFILE_DISABLE=1 tar -czf "$TARBALL" -C "$DAS_LAMBDA_CODE_LOCAL_DIR" \
        --exclude='das-lambda-java-sam/.ash' \
        --exclude='das-lambda-java-sam/.ash.yaml' \
        --exclude='das-lambda-java-sam/.DS_Store' \
        --exclude='das-lambda-java-sam/**/.DS_Store' \
        --exclude='das-lambda-java-sam/das_consumer_sam_project/database_activity_streams_event_consumer_function/target' \
        --exclude='das-lambda-java-sam/das_consumer_sam_project/database_activity_streams_event_consumer_function/.settings' \
        --exclude='das-lambda-java-sam/das_consumer_sam_project/database_activity_streams_event_consumer_function/.classpath' \
        --exclude='das-lambda-java-sam/das_consumer_sam_project/database_activity_streams_event_consumer_function/.project' \
        --exclude='das-lambda-java-sam/das_consumer_sam_project/.aws-sam' \
        das-lambda-java-sam
    aws s3 cp "$TARBALL" "s3://${CFT_BUCKET}/das-code.tgz" \
        --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager
    rm -f "$TARBALL"
    DAS_LAMBDA_CODE_S3_URI="s3://${CFT_BUCKET}/das-code.tgz"
    echo "  ✓ Code archive at $DAS_LAMBDA_CODE_S3_URI"
    echo ""
fi

# ---------- Build parameter overrides ----------
PARAM_OVERRIDES="CloudFrontPrefixListId=${CF_PREFIX_LIST_ID}"
if [ -n "$DAS_GITHUB_LOCATION" ]; then
    echo "DAS_GITHUB_LOCATION override: $DAS_GITHUB_LOCATION"
    PARAM_OVERRIDES="DASLambdaCodeGithubLocation=${DAS_GITHUB_LOCATION} ${PARAM_OVERRIDES}"
fi
if [ -n "$DAS_LAMBDA_CODE_S3_URI" ]; then
    echo "DAS_LAMBDA_CODE_S3_URI override: $DAS_LAMBDA_CODE_S3_URI"
    PARAM_OVERRIDES="DASLambdaCodeS3Uri=${DAS_LAMBDA_CODE_S3_URI} ${PARAM_OVERRIDES}"
fi
echo ""

# ---------- Deploy ----------
echo "Deploying CloudFormation stack '$STACK_NAME' (this takes 30-45 min)..."
DEPLOY_RC=0
aws cloudformation deploy \
    --template-file ./setup-das-cfn.yaml \
    --stack-name "$STACK_NAME" \
    --s3-bucket "$CFT_BUCKET" \
    --s3-prefix das \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-disable-rollback \
    --output json \
    --profile "$AWS_USER" \
    --region "$AWS_REGION" \
    --no-cli-pager \
    --parameter-overrides $PARAM_OVERRIDES \
    --no-fail-on-empty-changeset || DEPLOY_RC=$?

# ---------- Post-deploy verification ----------
# `aws cloudformation deploy` returns 0 for "no changes" too, so we always
# verify final stack status before claiming success.
echo ""
echo "Verifying final stack status..."
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --profile "$AWS_USER" --region "$AWS_REGION" \
    --query 'Stacks[0].StackStatus' --output text --no-cli-pager 2>/dev/null || echo "MISSING")

case "$STACK_STATUS" in
    CREATE_COMPLETE|UPDATE_COMPLETE|UPDATE_COMPLETE_CLEANUP_IN_PROGRESS)
        echo "  ✓ Stack status: $STACK_STATUS"
        if [ $DEPLOY_RC -ne 0 ]; then
            echo "  ⓘ Deploy command returned $DEPLOY_RC, but stack is healthy (likely 'no changes')."
        fi
        echo ""
        echo "Wait ~15 minutes for the EC2 UserData script to finish (RDS DAS"
        echo "enable, OSI pipeline create, SAM build/deploy)."
        exit 0
        ;;
    CREATE_FAILED|ROLLBACK_*|UPDATE_ROLLBACK_*|DELETE_FAILED)
        echo "  ✗ Stack status: $STACK_STATUS"
        echo ""
        echo "Recent failed events:"
        aws cloudformation describe-stack-events --stack-name "$STACK_NAME" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager \
            --query 'StackEvents[?contains(ResourceStatus, `FAILED`)].[Timestamp,LogicalResourceId,ResourceStatusReason]' \
            --output table 2>/dev/null | head -30 || true
        echo ""
        echo "Run cleanup-script.sh before retrying."
        exit 1
        ;;
    MISSING)
        echo "  ✗ Stack '$STACK_NAME' was not created."
        exit 1
        ;;
    *)
        echo "  ⚠ Stack status: $STACK_STATUS (unexpected)"
        exit 1
        ;;
esac
