#!/bin/bash
# Comprehensive cleanup script for the DAS Lambda Java SAM solution.
#
# Removes (in order): the SAM child stack, the DAS S3 bucket (including Object
# Lock retention), the OpenSearch Ingestion pipeline (releases requester-managed
# VPC endpoints before subnets get deleted), the main parent CloudFormation
# stack (with DeletionProtection on the RDS cluster handled automatically),
# the SAM bucket, the S3 logging bucket, the SAM-managed CloudFormation stack,
# the OpenSearch resource policy, the Bootstrap Secrets Manager secrets,
# the CFT packaging bucket, and orphaned resources from prior failed deletions.
#
# Idempotent — safe to re-run if a previous run partially failed.

# Use defensive, non-fatal mode so a single AWS call failure does not abort
# the whole cleanup. Each step explicitly handles its own error path.
set -uo pipefail

echo "=========================================="
echo "DAS Lambda Java SAM - Comprehensive Cleanup"
echo "=========================================="
echo ""

# ---------- 0a. Validate environment variables ----------
if [ -z "${AWS_USER:-}" ] || [ -z "${AWS_REGION:-}" ] || [ -z "${STACK_NAME:-}" ]; then
    echo "ERROR: Required environment variables are not set."
    echo "Please set: AWS_USER, AWS_REGION, and STACK_NAME"
    echo ""
    echo "Example:"
    echo "  export AWS_USER=<your-iam-user>"
    echo "  export AWS_REGION=<your-region>"
    echo "  export STACK_NAME=<your-stack-name>"
    exit 1
fi

echo "Configuration:"
echo "  AWS_USER:   $AWS_USER"
echo "  AWS_REGION: $AWS_REGION"
echo "  STACK_NAME: $STACK_NAME"
echo ""

# ---------- 0b. Validate AWS credentials ----------
echo "Verifying AWS credentials..."
if ! aws sts get-caller-identity --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1; then
    echo "ERROR: Cannot authenticate with profile '$AWS_USER' in region '$AWS_REGION'."
    echo "Run: aws sts get-caller-identity --profile $AWS_USER --region $AWS_REGION"
    echo "to diagnose."
    exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_USER" --region "$AWS_REGION" --query 'Account' --output text 2>/dev/null)
echo "  ✓ Authenticated as account $ACCOUNT_ID"
echo ""

# ---------- 0c. Detect candidate stacks and warn on STACK_NAME mismatch ----------
echo "Looking for related CloudFormation stacks..."
CANDIDATE_STACKS=$(aws cloudformation list-stacks \
    --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager \
    --query 'StackSummaries[?StackStatus!=`DELETE_COMPLETE` && (contains(StackName, `das`) || contains(StackName, `lambda`))].StackName' \
    --output text 2>/dev/null || echo "")

# Normalize whitespace (CLI text output is tab-separated) to one name per line
# so the exact-match check below is robust regardless of separator.
CANDIDATE_LIST=$(echo "$CANDIDATE_STACKS" | tr '\t' '\n')

if [ -z "$CANDIDATE_STACKS" ]; then
    echo "  ⓘ No active das/lambda stacks found in this account/region."
elif ! echo "$CANDIDATE_LIST" | grep -Fxq "$STACK_NAME"; then
    echo "  ⚠ STACK_NAME '$STACK_NAME' not found among active stacks: $CANDIDATE_STACKS"
    echo "  ⚠ Cleanup will still try, but you may have set the wrong STACK_NAME."
else
    echo "  ✓ Found target stack: $STACK_NAME"
fi
echo ""

# ---------- Helper: robust stack existence check ----------
# A bare `describe-stacks >/dev/null 2>&1` cannot tell "stack does not exist"
# apart from "the API call failed" (expired credentials, throttling, network).
# Treating an auth failure as "not found" causes the script to silently SKIP
# real deletions and still report success — exactly the failure mode seen when
# Midway/Isengard credentials expire partway through a long cleanup.
#
# stack_exists:
#   returns 0  -> stack exists
#   returns 1  -> stack definitively does NOT exist
#   exits 1    -> the API call failed for any other reason (abort loudly so the
#                 operator can re-authenticate and re-run; the script is
#                 idempotent and safe to re-run).
stack_exists() {
    local name="$1"
    local err
    err=$(aws cloudformation describe-stacks --stack-name "$name" \
        --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>&1 >/dev/null)
    if [ $? -eq 0 ]; then
        return 0
    fi
    case "$err" in
        *"does not exist"*|*"ValidationError"*)
            return 1
            ;;
        *)
            echo ""
            echo "ERROR: AWS API call failed while checking stack '$name'."
            echo "  $err"
            echo ""
            echo "This is NOT a 'stack not found' error — it usually means your"
            echo "credentials expired (run: mwinit / refresh the AWS profile) or"
            echo "the API is throttling. Aborting so we do not silently skip"
            echo "resource deletions. Re-authenticate and re-run this script —"
            echo "it is idempotent and safe to run again."
            exit 1
            ;;
    esac
}

# ---------- Helper: re-validate credentials before a destructive step ----------
# Cheap guard for the long-running phases (main stack delete can take 20+ min,
# well past a short credential lifetime).
require_creds() {
    if ! aws sts get-caller-identity --profile "$AWS_USER" \
            --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1; then
        echo ""
        echo "ERROR: AWS credentials for profile '$AWS_USER' are no longer valid"
        echo "(they may have expired mid-run). Re-authenticate (mwinit / refresh"
        echo "the profile) and re-run this script — it is idempotent."
        exit 1
    fi
}

# ---------- Step 1/17: Delete RetrieveAOSPassword Lambda directly ----------
# Tracks whether any critical step (e.g. main stack deletion) failed, so the
# final summary reports honestly instead of always printing success.
CLEANUP_HAD_FAILURES=0

# Background: this Lambda was added in Phase 1 to retrieve the OpenSearch
# password from Secrets Manager during stack creation. Deleting it directly
# before the parent stack reduces churn during stack delete.
echo "[1/17] Checking for orphaned RetrieveAOSPassword Lambda..."
RETRIEVE_AOS_LAMBDAS=$(aws lambda list-functions --profile "$AWS_USER" --region "$AWS_REGION" \
    --query "Functions[?contains(FunctionName, 'RetrieveAOSPassword')].FunctionName" \
    --output text --no-cli-pager 2>/dev/null || echo "")
if [ -n "$RETRIEVE_AOS_LAMBDAS" ]; then
    for LAMBDA_NAME in $RETRIEVE_AOS_LAMBDAS; do
        if aws lambda delete-function --function-name "$LAMBDA_NAME" \
                --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null; then
            echo "  ✓ Deleted Lambda: $LAMBDA_NAME"
        else
            echo "  ⓘ Could not delete Lambda $LAMBDA_NAME (may already be gone)"
        fi
    done
else
    echo "  ⓘ No RetrieveAOSPassword Lambda found, skipping..."
fi
echo ""

# ---------- Step 2/17: Delete SAM child stack (das-lambda-stack) ----------
echo "[2/17] Deleting SAM child stack (das-lambda-stack)..."
if stack_exists das-lambda-stack; then
    aws cloudformation delete-stack --stack-name das-lambda-stack \
        --region "$AWS_REGION" --profile "$AWS_USER" 2>/dev/null || true
    echo "  Waiting for SAM child stack deletion..."
    if aws cloudformation wait stack-delete-complete --stack-name das-lambda-stack \
            --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null; then
        echo "  ✓ SAM child stack deleted"
    else
        echo "  ⚠ Wait returned non-zero. Continuing — main stack delete will retry."
    fi
else
    echo "  ⓘ SAM child stack not found, skipping..."
fi
echo ""

# ---------- Step 3/17: Empty the DAS S3 bucket ----------
# Object Lock retention must be removed before object versions can be deleted.
echo "[3/17] Emptying DAS S3 bucket (Object Lock aware)..."
DAS_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --profile "$AWS_USER" --region "$AWS_REGION" \
    --query "Stacks[*].Outputs[?OutputKey=='S3BucketName'].OutputValue" \
    --output text --no-cli-pager 2>/dev/null || echo "")
if [ -n "$DAS_BUCKET_NAME" ] && [ "$DAS_BUCKET_NAME" != "None" ]; then
    echo "  Bucket name: $DAS_BUCKET_NAME"

    OBJECT_LOCK_ENABLED=$(aws s3api get-object-lock-configuration --bucket "$DAS_BUCKET_NAME" \
        --profile "$AWS_USER" 2>/dev/null \
        | jq -r '.ObjectLockConfiguration.ObjectLockEnabled' 2>/dev/null || echo "")

    if [ "$OBJECT_LOCK_ENABLED" == "Enabled" ]; then
        echo "  Object Lock enabled — clearing retention on all versions..."
        aws s3api list-object-versions --bucket "$DAS_BUCKET_NAME" --profile "$AWS_USER" \
            --query 'Versions[].{Key:Key,VersionId:VersionId}' --output json 2>/dev/null \
            | jq -c '.[]?' 2>/dev/null | while read -r obj; do
                KEY=$(echo "$obj" | jq -r '.Key')
                VERSION_ID=$(echo "$obj" | jq -r '.VersionId')
                aws s3api put-object-retention --bucket "$DAS_BUCKET_NAME" \
                    --key "$KEY" --version-id "$VERSION_ID" \
                    --retention '{}' --bypass-governance-retention \
                    --profile "$AWS_USER" 2>/dev/null || true
            done
    fi

    # Delete versions, then delete markers (order matters to avoid creating new markers)
    VERSIONS=$(aws s3api list-object-versions --profile "$AWS_USER" --bucket "$DAS_BUCKET_NAME" \
        --query='{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null \
        || echo '{"Objects":[]}')
    if [ "$VERSIONS" != '{"Objects":[]}' ] && [ "$VERSIONS" != '{"Objects":null}' ]; then
        aws s3api delete-objects --profile "$AWS_USER" --bucket "$DAS_BUCKET_NAME" \
            --delete "$VERSIONS" --bypass-governance-retention \
            --no-cli-pager --output text 2>/dev/null || true
    fi

    DELETE_MARKERS=$(aws s3api list-object-versions --profile "$AWS_USER" --bucket "$DAS_BUCKET_NAME" \
        --query='{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null \
        || echo '{"Objects":[]}')
    if [ "$DELETE_MARKERS" != '{"Objects":[]}' ] && [ "$DELETE_MARKERS" != '{"Objects":null}' ]; then
        aws s3api delete-objects --profile "$AWS_USER" --bucket "$DAS_BUCKET_NAME" \
            --delete "$DELETE_MARKERS" --no-cli-pager --output text 2>/dev/null || true
    fi

    # Final sweep: anything still left
    aws s3 rm "s3://$DAS_BUCKET_NAME" --recursive --profile "$AWS_USER" 2>/dev/null || true
    echo "  ✓ DAS bucket emptied"
else
    echo "  ⓘ DAS bucket not found (stack may not exist yet), skipping..."
fi
echo ""

# ---------- Step 4/17: Capture S3 Logging bucket name before stack deletion ----------
echo "[4/17] Capturing S3 Logging bucket name..."
S3_LOGGING_BUCKET=""
if stack_exists "$STACK_NAME"; then
    S3_LOGGING_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
        --profile "$AWS_USER" --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='S3LoggingBucketName'].OutputValue" \
        --output text --no-cli-pager 2>/dev/null || echo "")
    if [ -z "$S3_LOGGING_BUCKET" ] || [ "$S3_LOGGING_BUCKET" == "None" ]; then
        S3_LOGGING_BUCKET=$(aws cloudformation describe-stack-resources --stack-name "$STACK_NAME" \
            --profile "$AWS_USER" --region "$AWS_REGION" \
            --query "StackResources[?LogicalResourceId=='S3LoggingBucket'].PhysicalResourceId" \
            --output text --no-cli-pager 2>/dev/null || echo "")
    fi
    if [ -n "$S3_LOGGING_BUCKET" ] && [ "$S3_LOGGING_BUCKET" != "None" ]; then
        echo "  ✓ Captured: $S3_LOGGING_BUCKET"
    else
        echo "  ⓘ S3 Logging bucket not found in stack outputs"
        S3_LOGGING_BUCKET=""
    fi
else
    echo "  ⓘ Stack not found, skipping..."
fi
echo ""

# ---------- Step 5/17: Disable RDS DeletionProtection ----------
echo "[5/17] Checking RDS cluster DeletionProtection..."
RDS_CLUSTER_IDS=$(aws rds describe-db-clusters --profile "$AWS_USER" --region "$AWS_REGION" \
    --query "DBClusters[?contains(DBClusterIdentifier, \`${STACK_NAME}\`)].DBClusterIdentifier" \
    --output text 2>/dev/null || echo "")
if [ -n "$RDS_CLUSTER_IDS" ]; then
    for RDS_CLUSTER_ID in $RDS_CLUSTER_IDS; do
        DELETION_PROTECTION=$(aws rds describe-db-clusters \
            --profile "$AWS_USER" --region "$AWS_REGION" \
            --db-cluster-identifier "$RDS_CLUSTER_ID" \
            --query 'DBClusters[0].DeletionProtection' --output text 2>/dev/null || echo "false")

        if [ "$DELETION_PROTECTION" == "True" ] || [ "$DELETION_PROTECTION" == "true" ]; then
            echo "  ⚠ DeletionProtection enabled on $RDS_CLUSTER_ID — disabling..."
            aws rds modify-db-cluster \
                --db-cluster-identifier "$RDS_CLUSTER_ID" \
                --no-deletion-protection \
                --apply-immediately \
                --profile "$AWS_USER" --region "$AWS_REGION" \
                --no-cli-pager > /dev/null 2>&1 || true

            # Wait for the modification to actually complete; --apply-immediately
            # moves the cluster to 'modifying' state for ~30-90s, and a stack
            # delete during that window fails with InvalidDBClusterStateFault.
            echo "  Waiting for cluster modification to complete..."
            if aws rds wait db-cluster-available \
                    --db-cluster-identifier "$RDS_CLUSTER_ID" \
                    --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null; then
                echo "  ✓ DeletionProtection disabled and cluster available"
            else
                echo "  ⚠ Wait returned non-zero. Continuing — stack delete will retry."
            fi
        else
            echo "  ✓ DeletionProtection already disabled on $RDS_CLUSTER_ID"
        fi
    done
else
    echo "  ⓘ No RDS cluster found for stack $STACK_NAME, skipping..."
fi
echo ""

# ---------- Step 6/17: Delete OSI pipeline before main stack ----------
# The OSI pipeline creates requester-managed VPC endpoints in private subnets.
# These endpoints (and their ENIs) block subnet deletion if not removed first.
echo "[6/17] Deleting OpenSearch Ingestion pipeline (releases VPC endpoints)..."
if aws osis get-pipeline --pipeline-name "das-osi-pipeline" \
        --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1; then
    aws osis delete-pipeline --pipeline-name "das-osi-pipeline" \
        --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null || true
    echo "  ✓ Pipeline deletion initiated"

    echo "  Waiting for pipeline + VPC endpoint cleanup (up to 5 min)..."
    PIPELINE_WAIT=0
    while [ $PIPELINE_WAIT -lt 300 ]; do
        PIPELINE_STATUS=$(aws osis get-pipeline --pipeline-name "das-osi-pipeline" \
            --profile "$AWS_USER" --region "$AWS_REGION" \
            --query "Pipeline.Status" --output text --no-cli-pager 2>/dev/null || echo "DELETED")
        if [ "$PIPELINE_STATUS" = "DELETED" ] || [ -z "$PIPELINE_STATUS" ]; then
            echo "  ✓ Pipeline fully deleted"
            break
        fi
        echo "  Status: $PIPELINE_STATUS, waiting 15s..."
        sleep 15
        PIPELINE_WAIT=$((PIPELINE_WAIT + 15))
    done
    echo "  Waiting 30s for ENIs to be released..."
    sleep 30
else
    echo "  ⓘ OSI pipeline not found, skipping..."
fi
echo ""

# ---------- Step 7/17: Delete main CloudFormation stack ----------
echo "[7/17] Deleting main CloudFormation stack ($STACK_NAME)..."
require_creds
if stack_exists "$STACK_NAME"; then
    echo "  Attempting standard deletion (15-25 min)..."
    aws cloudformation delete-stack --stack-name "$STACK_NAME" \
        --deletion-mode STANDARD --region "$AWS_REGION" --profile "$AWS_USER" 2>/dev/null || true

    WAIT_RESULT=0
    aws cloudformation wait stack-delete-complete \
        --stack-name "$STACK_NAME" --profile "$AWS_USER" --region "$AWS_REGION" \
        2>/dev/null || WAIT_RESULT=$?

    if [ $WAIT_RESULT -ne 0 ]; then
        echo "  ⚠ Standard deletion failed, attempting force delete..."
        require_creds
        if stack_exists "$STACK_NAME"; then
            aws cloudformation delete-stack --stack-name "$STACK_NAME" \
                --deletion-mode FORCE_DELETE_STACK \
                --region "$AWS_REGION" --profile "$AWS_USER" 2>/dev/null || true
            aws cloudformation wait stack-delete-complete \
                --stack-name "$STACK_NAME" --profile "$AWS_USER" --region "$AWS_REGION" \
                2>/dev/null || true
        fi
    fi

    # Honest verification: confirm the stack is actually gone before claiming success.
    if stack_exists "$STACK_NAME"; then
        echo "  ✗ Main stack still exists after delete attempts. Check the"
        echo "    CloudFormation console for the blocking resource and re-run."
        CLEANUP_HAD_FAILURES=1
    else
        echo "  ✓ Main stack deleted"
    fi
else
    echo "  ⓘ Main stack not found, skipping..."
fi
echo ""

# ---------- Helper: empty an S3 bucket including versions and Object Lock ----------
# Loops until the bucket reports zero versions AND zero delete markers, because
# 'aws s3 rm --recursive' on a versioned bucket creates new delete markers and
# S3's eventual consistency can leave residual versions after a single pass.
# Returns 0 when empty, 1 if it couldn't be emptied after MAX passes.
empty_bucket() {
    local BUCKET="$1"
    [ -z "$BUCKET" ] && return 0
    if ! aws s3api head-bucket --bucket "$BUCKET" --profile "$AWS_USER" 2>/dev/null; then
        return 0
    fi

    # Clear Object Lock retention up front (once) if enabled.
    local LOCK
    LOCK=$(aws s3api get-object-lock-configuration --bucket "$BUCKET" --profile "$AWS_USER" 2>/dev/null \
        | jq -r '.ObjectLockConfiguration.ObjectLockEnabled' 2>/dev/null || echo "")
    if [ "$LOCK" == "Enabled" ]; then
        aws s3api list-object-versions --bucket "$BUCKET" --profile "$AWS_USER" \
            --query 'Versions[].{Key:Key,VersionId:VersionId}' --output json 2>/dev/null \
            | jq -c '.[]?' 2>/dev/null | while read -r obj; do
                KEY=$(echo "$obj" | jq -r '.Key')
                VID=$(echo "$obj" | jq -r '.VersionId')
                aws s3api put-object-retention --bucket "$BUCKET" \
                    --key "$KEY" --version-id "$VID" \
                    --retention '{}' --bypass-governance-retention \
                    --profile "$AWS_USER" 2>/dev/null || true
            done
    fi

    local pass=0
    while [ $pass -lt 6 ]; do
        pass=$((pass + 1))

        # Delete all object versions and delete markers directly via the S3 API.
        # We intentionally do NOT use `aws s3 rm --recursive` here: on a
        # versioned bucket it only adds new delete markers (it never removes
        # versions), which churns state and races CloudFormation's own
        # bucket-empty check during stack deletion.

        # Delete all object versions.
        local V
        V=$(aws s3api list-object-versions --profile "$AWS_USER" --bucket "$BUCKET" \
            --query='{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null \
            || echo '{"Objects":[]}')
        if [ "$V" != '{"Objects":[]}' ] && [ "$V" != '{"Objects":null}' ]; then
            aws s3api delete-objects --profile "$AWS_USER" --bucket "$BUCKET" \
                --delete "$V" --bypass-governance-retention \
                --no-cli-pager --output text 2>/dev/null || true
        fi

        # Delete all delete markers.
        local DM
        DM=$(aws s3api list-object-versions --profile "$AWS_USER" --bucket "$BUCKET" \
            --query='{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null \
            || echo '{"Objects":[]}')
        if [ "$DM" != '{"Objects":[]}' ] && [ "$DM" != '{"Objects":null}' ]; then
            aws s3api delete-objects --profile "$AWS_USER" --bucket "$BUCKET" \
                --delete "$DM" --no-cli-pager --output text 2>/dev/null || true
        fi

        # Check emptiness: count remaining versions + delete markers.
        local REMAINING
        REMAINING=$(aws s3api list-object-versions --profile "$AWS_USER" --bucket "$BUCKET" \
            --query 'length(Versions || `[]`) + length(DeleteMarkers || `[]`)' \
            --output text 2>/dev/null || echo "0")
        if [ "$REMAINING" = "0" ] || [ -z "$REMAINING" ]; then
            return 0
        fi
        sleep 3
    done

    echo "  ⚠ Bucket $BUCKET still not empty after $pass passes"
    return 1
}

# ---------- Step 8/17: Empty SAM-managed bucket(s) ----------
echo "[8/17] Emptying SAM CLI managed bucket(s)..."
SAM_BUCKETS=$(aws s3api list-buckets \
    --query "Buckets[?starts_with(Name, 'aws-sam-cli-')].Name" \
    --profile "$AWS_USER" --no-cli-pager --output text 2>/dev/null || echo "")
if [ -n "$SAM_BUCKETS" ]; then
    for B in $SAM_BUCKETS; do
        echo "  Emptying $B..."
        empty_bucket "$B"
        echo "  ✓ Emptied $B"
    done
else
    echo "  ⓘ No SAM buckets found, skipping..."
fi
echo ""

# ---------- Step 9/17: Empty S3 Logging bucket ----------
echo "[9/17] Emptying S3 Logging bucket..."
if [ -n "$S3_LOGGING_BUCKET" ]; then
    echo "  Emptying $S3_LOGGING_BUCKET..."
    empty_bucket "$S3_LOGGING_BUCKET"
    echo "  ✓ Emptied"
else
    echo "  ⓘ No S3 Logging bucket captured, skipping..."
fi
echo ""

# ---------- Step 10/17: Delete aws-sam-cli-managed-default stack ----------
echo "[10/17] Deleting aws-sam-cli-managed-default CloudFormation stack..."
if stack_exists aws-sam-cli-managed-default; then
    if [ -n "$SAM_BUCKETS" ]; then
        for B in $SAM_BUCKETS; do
            empty_bucket "$B"
        done
    fi
    aws cloudformation delete-stack --stack-name aws-sam-cli-managed-default \
        --deletion-mode STANDARD --region "$AWS_REGION" --profile "$AWS_USER" 2>/dev/null || true
    if aws cloudformation wait stack-delete-complete --stack-name aws-sam-cli-managed-default \
            --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null; then
        echo "  ✓ SAM managed stack deleted"
    else
        # Most common cause: the SamCliSourceBucket re-accumulated versions
        # (it's a versioned bucket). Re-empty thoroughly and retry once.
        echo "  ⚠ First delete attempt failed — re-emptying SAM bucket(s) and retrying..."
        if [ -n "$SAM_BUCKETS" ]; then
            for B in $SAM_BUCKETS; do
                empty_bucket "$B"
            done
        fi
        aws cloudformation delete-stack --stack-name aws-sam-cli-managed-default \
            --deletion-mode STANDARD --region "$AWS_REGION" --profile "$AWS_USER" 2>/dev/null || true
        if aws cloudformation wait stack-delete-complete --stack-name aws-sam-cli-managed-default \
                --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null; then
            echo "  ✓ SAM managed stack deleted on retry"
        else
            echo "  ⚠ SAM stack still not deleted. Check console for aws-sam-cli-managed-default."
        fi
    fi
else
    echo "  ⓘ SAM managed stack not found, skipping..."
fi
echo ""

# ---------- Step 11/17: Verify OSI pipeline gone ----------
echo "[11/17] Verifying OSI pipeline is gone..."
if aws osis get-pipeline --pipeline-name "das-osi-pipeline" \
        --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1; then
    PIPELINE_STATUS=$(aws osis get-pipeline --pipeline-name "das-osi-pipeline" \
        --profile "$AWS_USER" --region "$AWS_REGION" \
        --query "Pipeline.Status" --output text --no-cli-pager 2>/dev/null || echo "DELETED")
    if [ "$PIPELINE_STATUS" != "DELETING" ] && [ "$PIPELINE_STATUS" != "DELETED" ] && [ -n "$PIPELINE_STATUS" ]; then
        echo "  Pipeline lingering ($PIPELINE_STATUS), re-deleting..."
        aws osis delete-pipeline --pipeline-name "das-osi-pipeline" \
            --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null || true
    else
        echo "  ✓ Pipeline already deleted or deleting"
    fi
else
    echo "  ✓ Pipeline confirmed gone"
fi
echo ""

# ---------- Step 12/17: Delete CloudWatch log groups ----------
# CloudFormation doesn't own log groups created at first Lambda invocation,
# so they outlive the stack. Same name on redeploy → "log group already exists".
#
# CloudFormation truncates Lambda physical names to fit within the 64-char
# Lambda name limit, so log group prefixes can be a SHORTER variant of
# $STACK_NAME (e.g. 'das-lambda-serverless-samples' → 'das-lambda-serverless-sam').
# We compute the longest common prefix of the stack name we can match safely
# (everything up to and including the first 'unique' segment), then filter.
echo "[12/17] Deleting orphaned CloudWatch log groups..."

# Use the first 4 chars of the stack name as a safe match key. This catches
# both full-name and CFN-truncated variants while still being specific to
# this stack family. For a stack named 'das-lambda-foo' we match prefix
# '/aws/lambda/das-' which we then narrow down via substring matching below.
SHORT_STACK_KEY=$(echo "$STACK_NAME" | cut -c1-4)
LAMBDA_BROAD_PREFIX="/aws/lambda/${SHORT_STACK_KEY}"

# Enumerate all candidate log groups under the broad prefix, then keep only
# those whose name starts with a prefix derived from $STACK_NAME (allowing
# for CFN truncation). The minimum sensible match length is 8 chars after
# '/aws/lambda/' to avoid hitting unrelated stacks.
CANDIDATES=$(aws logs describe-log-groups \
    --log-group-name-prefix "$LAMBDA_BROAD_PREFIX" \
    --profile "$AWS_USER" --region "$AWS_REGION" \
    --query 'logGroups[].logGroupName' --output json --no-cli-pager 2>/dev/null \
    | jq -r '.[]?' 2>/dev/null || echo "")

# Build a list of acceptable stack-name prefixes: the full name down to a
# 12-char minimum (anything shorter risks matching unrelated stacks).
MATCHED_GROUPS=""
if [ -n "$CANDIDATES" ]; then
    # We require the log-group portion after '/aws/lambda/' to start with
    # at least the first 12 chars of $STACK_NAME; this lets us match the
    # CFN-truncated forms reliably.
    STACK_LEN=${#STACK_NAME}
    MIN_PREFIX_LEN=12
    if [ $STACK_LEN -lt $MIN_PREFIX_LEN ]; then
        MIN_PREFIX_LEN=$STACK_LEN
    fi
    for LG in $CANDIDATES; do
        # Strip '/aws/lambda/' prefix to get the bare log-group name
        BARE="${LG#/aws/lambda/}"
        # Check if STACK_NAME (or any truncation thereof down to MIN_PREFIX_LEN)
        # is a prefix of BARE. Uses POSIX while + case (portable to dash).
        i=$STACK_LEN
        while [ "$i" -ge "$MIN_PREFIX_LEN" ]; do
            CANDIDATE_PREFIX=$(echo "$STACK_NAME" | cut -c1-"$i")
            case "$BARE" in
                "${CANDIDATE_PREFIX}-"*)
                    MATCHED_GROUPS="$MATCHED_GROUPS $LG"
                    break
                    ;;
            esac
            i=$((i - 1))
        done
    done
fi

# Also include the SAM child stack, OpenSearch/OSI vendedlogs, and the RDS
# cluster log groups for this stack. Space-delimited list iterated by a POSIX
# for loop (no bash arrays). These prefixes contain no spaces or glob
# characters, so word-splitting is safe and the loop stays in the current
# shell (so MATCHED_GROUPS persists).
EXTRA_PREFIXES="/aws/lambda/das-lambda-stack- /aws/vendedlogs/OpenSearchService/${STACK_NAME}- /aws/osis/${STACK_NAME}- /aws/rds/cluster/${STACK_NAME}-"
for PREFIX in $EXTRA_PREFIXES; do
    LOG_GROUPS=$(aws logs describe-log-groups \
        --log-group-name-prefix "$PREFIX" \
        --profile "$AWS_USER" --region "$AWS_REGION" \
        --query 'logGroups[].logGroupName' --output json --no-cli-pager 2>/dev/null \
        | jq -r '.[]?' 2>/dev/null || echo "")
    [ -n "$LOG_GROUPS" ] && MATCHED_GROUPS="$MATCHED_GROUPS $LOG_GROUPS"
done

# OpenSearch domain log groups live at /aws/opensearch/<DomainName>/* where
# DomainName is NOT prefixed by the stack name, so a stack-scoped prefix can't
# match them. Enumerate the /aws/opensearch/ namespace and keep only the
# das-lambda domains (mirrors the orphaned-domain sweep below). These groups
# have DeletionPolicy: Delete in the template but persist after a force-deleted
# or failed parent-stack deletion, and their fixed names then cause a
# NAME_CONFLICT pre-deployment validation error on the next deploy.
OS_LOG_GROUPS=$(aws logs describe-log-groups \
    --log-group-name-prefix "/aws/opensearch/" \
    --profile "$AWS_USER" --region "$AWS_REGION" \
    --query "logGroups[?contains(logGroupName, 'das-lambda')].logGroupName" \
    --output json --no-cli-pager 2>/dev/null \
    | jq -r '.[]?' 2>/dev/null || echo "")
[ -n "$OS_LOG_GROUPS" ] && MATCHED_GROUPS="$MATCHED_GROUPS $OS_LOG_GROUPS"

# Delete each matched log group (deduplicated)
DELETED_COUNT=0
for LG in $(echo "$MATCHED_GROUPS" | tr ' ' '\n' | sort -u); do
    [ -z "$LG" ] && continue
    if aws logs delete-log-group --log-group-name "$LG" \
            --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null; then
        echo "  ✓ Deleted log group: $LG"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    else
        echo "  ⓘ Could not delete: $LG"
    fi
done
echo "  ✓ Log group cleanup completed ($DELETED_COUNT deleted)"
echo ""

# ---------- Step 13/17: Delete OpenSearch resource policy ----------
# Created by the EnableOpenSearchLogging custom resource; CFN does not manage
# its lifecycle, so it lingers between deploys.
echo "[13/17] Deleting CloudWatch resource policy 'OpenSearchLogsPolicy'..."
if aws logs describe-resource-policies --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null \
        | jq -e '.resourcePolicies[]? | select(.policyName=="OpenSearchLogsPolicy")' > /dev/null 2>&1; then
    if aws logs delete-resource-policy --policy-name OpenSearchLogsPolicy \
            --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null; then
        echo "  ✓ Deleted resource policy: OpenSearchLogsPolicy"
    else
        echo "  ⓘ Could not delete OpenSearchLogsPolicy (may already be gone)"
    fi
else
    echo "  ⓘ OpenSearchLogsPolicy not found, skipping..."
fi
echo ""

# ---------- Step 14/17: Delete bootstrap Secrets Manager secrets ----------
# These are only created by BootStrapFromCloudShellNoConsoleAccess.sh (Option 2).
# Console-access users (Option 1) won't have them, so we check before deleting
# to keep output clean.
echo "[14/17] Deleting bootstrap Secrets Manager secrets (if any)..."
for SECRET in aws-access-key-id aws-secret-access-key; do
    if aws secretsmanager describe-secret --secret-id "$SECRET" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1; then
        if aws secretsmanager delete-secret --secret-id "$SECRET" \
                --force-delete-without-recovery \
                --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1; then
            echo "  ✓ Deleted bootstrap secret: $SECRET"
        else
            echo "  ⓘ Could not delete bootstrap secret: $SECRET"
        fi
    fi
done
echo ""

# ---------- Step 15/17: Empty and delete CFT packaging bucket(s) ----------
echo "[15/17] Emptying and deleting CFT packaging bucket(s)..."
CFT_BUCKETS=$(aws s3api list-buckets \
    --query "Buckets[?starts_with(Name, 'cft-bucket-${ACCOUNT_ID}-')].Name" \
    --profile "$AWS_USER" --no-cli-pager --output text 2>/dev/null || echo "")
if [ -n "$CFT_BUCKETS" ]; then
    for B in $CFT_BUCKETS; do
        empty_bucket "$B"
        # CFT packaging buckets are created with `aws s3 mb` and are NOT
        # versioned. empty_bucket targets object *versions*, so the current
        # (non-versioned) objects — the uploaded template and code archive —
        # can remain, which makes delete-bucket fail with BucketNotEmpty. A
        # plain recursive remove reliably clears current objects here. (Safe
        # for this bucket because it is deleted directly by the script, not by
        # CloudFormation, so the delete-marker concern in empty_bucket does not
        # apply.)
        aws s3 rm "s3://$B" --recursive \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager >/dev/null 2>&1 || true
        if aws s3api delete-bucket --bucket "$B" --region "$AWS_REGION" \
                --profile "$AWS_USER" 2>/dev/null; then
            echo "  ✓ Deleted CFT bucket: $B"
        else
            echo "  ⓘ Could not delete CFT bucket: $B"
        fi
    done
else
    echo "  ⓘ No CFT buckets found, skipping..."
fi
echo ""

# ---------- Step 16/17: KMS key cleanup verification ----------
# CFN schedules CMK deletion during stack delete (7-day pending window). Here
# we just check for orphaned keys with the stack tag.
echo "[16/17] Verifying KMS key cleanup..."
if stack_exists "$STACK_NAME"; then
    echo "  ⓘ Stack still exists, KMS keys will be scheduled for deletion when stack deletes"
else
    echo "  Looking for orphaned customer-managed KMS keys with StackName tag..."
    KMS_KEYS=$(aws kms list-keys --profile "$AWS_USER" --region "$AWS_REGION" \
        --query 'Keys[].KeyId' --output text 2>/dev/null || echo "")
    SCHEDULED=0
    if [ -n "$KMS_KEYS" ]; then
        for KEY_ID in $KMS_KEYS; do
            # Skip AWS-managed keys and keys already pending deletion
            META=$(aws kms describe-key --key-id "$KEY_ID" \
                --profile "$AWS_USER" --region "$AWS_REGION" \
                --query 'KeyMetadata.[KeyManager,KeyState]' --output text \
                --no-cli-pager 2>/dev/null || echo "")
            MGR=$(echo "$META" | awk '{print $1}')
            STATE=$(echo "$META" | awk '{print $2}')
            [ "$MGR" != "CUSTOMER" ] && continue
            [ "$STATE" = "PendingDeletion" ] && continue

            TAGS=$(aws kms list-resource-tags --key-id "$KEY_ID" \
                --profile "$AWS_USER" --region "$AWS_REGION" \
                --query 'Tags[?TagKey==`StackName`].TagValue' --output text \
                --no-cli-pager 2>/dev/null || echo "")
            if [ "$TAGS" = "$STACK_NAME" ]; then
                if aws kms schedule-key-deletion --key-id "$KEY_ID" \
                        --pending-window-in-days 7 \
                        --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null > /dev/null; then
                    echo "  ✓ Orphaned key $KEY_ID scheduled for deletion in 7 days"
                    SCHEDULED=$((SCHEDULED + 1))
                fi
            fi
        done
    fi
    if [ $SCHEDULED -eq 0 ]; then
        echo "  ⓘ No orphaned customer-managed KMS keys with StackName=$STACK_NAME tag found"
    fi
fi
echo ""

# ---------- Step 17/17: Cleanup orphaned RDS, subnet groups, instance profiles ----------
echo "[17/17] Cleaning up orphaned resources from prior failed deletions..."

echo "  Checking for orphaned RDS clusters..."
ORPHANED_CLUSTERS=$(aws rds describe-db-clusters --profile "$AWS_USER" --region "$AWS_REGION" \
    --query "DBClusters[?contains(DBClusterIdentifier, 'das-lambda')].{Id:DBClusterIdentifier,Protected:DeletionProtection}" \
    --output json 2>/dev/null || echo "[]")
if [ "$ORPHANED_CLUSTERS" != "[]" ]; then
    echo "$ORPHANED_CLUSTERS" | jq -c '.[]?' 2>/dev/null | while read -r cluster; do
        CLUSTER_ID=$(echo "$cluster" | jq -r '.Id')
        PROTECTED=$(echo "$cluster" | jq -r '.Protected')
        echo "  Orphaned cluster: $CLUSTER_ID (protected=$PROTECTED)"
        if [ "$PROTECTED" == "true" ]; then
            aws rds modify-db-cluster --db-cluster-identifier "$CLUSTER_ID" \
                --no-deletion-protection --apply-immediately \
                --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1 || true
            aws rds wait db-cluster-available --db-cluster-identifier "$CLUSTER_ID" \
                --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null || true
        fi
        INSTANCES=$(aws rds describe-db-instances --profile "$AWS_USER" --region "$AWS_REGION" \
            --query "DBInstances[?DBClusterIdentifier=='$CLUSTER_ID'].DBInstanceIdentifier" \
            --output text 2>/dev/null || echo "")
        for INST in $INSTANCES; do
            aws rds delete-db-instance --db-instance-identifier "$INST" \
                --skip-final-snapshot \
                --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1 || true
        done
        if aws rds delete-db-cluster --db-cluster-identifier "$CLUSTER_ID" \
                --skip-final-snapshot \
                --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager > /dev/null 2>&1; then
            echo "    ✓ Cluster $CLUSTER_ID deleted"
        else
            echo "    ⓘ Could not delete cluster $CLUSTER_ID"
        fi
    done
else
    echo "  ⓘ No orphaned RDS clusters found"
fi

echo "  Waiting 30s for RDS deletions to release subnet groups..."
sleep 30

echo "  Checking for orphaned DB subnet groups..."
ORPHANED_SG=$(aws rds describe-db-subnet-groups --profile "$AWS_USER" --region "$AWS_REGION" \
    --query "DBSubnetGroups[?contains(DBSubnetGroupName, 'das-lambda')].DBSubnetGroupName" \
    --output text 2>/dev/null || echo "")
for SG in $ORPHANED_SG; do
    if aws rds delete-db-subnet-group --db-subnet-group-name "$SG" \
            --profile "$AWS_USER" --region "$AWS_REGION" 2>/dev/null; then
        echo "  ✓ Subnet group $SG deleted"
    else
        echo "  ⓘ Could not delete $SG (may still be in use)"
    fi
done

echo "  Checking for orphaned instance profiles..."
ORPHANED_PROFILES=$(aws iam list-instance-profiles --profile "$AWS_USER" \
    --query "InstanceProfiles[?contains(InstanceProfileName, 'EC2MMMSKCFProfile')].InstanceProfileName" \
    --output text --no-cli-pager 2>/dev/null || echo "")
for PROFILE in $ORPHANED_PROFILES; do
    ROLES=$(aws iam get-instance-profile --instance-profile-name "$PROFILE" \
        --profile "$AWS_USER" --query "InstanceProfile.Roles[].RoleName" \
        --output text --no-cli-pager 2>/dev/null || echo "")
    for ROLE in $ROLES; do
        aws iam remove-role-from-instance-profile \
            --instance-profile-name "$PROFILE" --role-name "$ROLE" \
            --profile "$AWS_USER" 2>/dev/null || true
    done
    if aws iam delete-instance-profile --instance-profile-name "$PROFILE" \
            --profile "$AWS_USER" 2>/dev/null; then
        echo "  ✓ Instance profile $PROFILE deleted"
    else
        echo "  ⓘ Could not delete $PROFILE"
    fi
done

# Orphaned OpenSearch domains. A force-deleted or timed-out parent stack can
# leave the domain behind; its requester-managed ENIs stay in-use and block
# VPC deletion (the failure mode seen in Checkpoint 6). Delete matching domains
# and wait for them to disappear so their ENIs release before the VPC step.
echo "  Checking for orphaned OpenSearch domains..."
ORPHANED_DOMAINS=$(aws opensearch list-domain-names \
    --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager \
    --query "DomainNames[?contains(DomainName, 'das-lambda')].DomainName" \
    --output text 2>/dev/null || echo "")
for DOMAIN in $ORPHANED_DOMAINS; do
    echo "  Found orphaned OpenSearch domain: $DOMAIN — deleting..."
    aws opensearch delete-domain --domain-name "$DOMAIN" \
        --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
done
if [ -n "$ORPHANED_DOMAINS" ]; then
    echo "  Waiting for OpenSearch domain(s) to delete and release ENIs (up to 30 min)..."
    DOMAIN_WAIT=0
    while [ $DOMAIN_WAIT -lt 1800 ]; do
        STILL=$(aws opensearch list-domain-names \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager \
            --query "DomainNames[?contains(DomainName, 'das-lambda')].DomainName" \
            --output text 2>/dev/null || echo "")
        if [ -z "$STILL" ]; then
            echo "  ✓ OpenSearch domain(s) fully deleted"
            break
        fi
        echo "  Still deleting: $STILL — waiting 60s..."
        sleep 60
        DOMAIN_WAIT=$((DOMAIN_WAIT + 60))
    done
    # Give the requester-managed ENIs a moment to detach after domain deletion.
    sleep 30
else
    echo "  ⓘ No orphaned OpenSearch domains found"
fi

# Orphaned VPCs from prior failed deployments. CFN tags VPCs with
# 'aws:cloudformation:stack-name' on creation; these tags survive even when
# the stack itself is gone, so we can identify orphans reliably by tag.
echo "  Checking for orphaned VPCs tagged with this stack name..."
ORPHANED_VPCS=$(aws ec2 describe-vpcs --profile "$AWS_USER" --region "$AWS_REGION" \
    --filters "Name=tag:aws:cloudformation:stack-name,Values=${STACK_NAME}" \
    --query 'Vpcs[].VpcId' --output text --no-cli-pager 2>/dev/null || echo "")
for VPC_ID in $ORPHANED_VPCS; do
    echo "  Found orphaned VPC: $VPC_ID — attempting cleanup..."

    # Detach + delete internet gateways first (they block VPC deletion)
    IGWS=$(aws ec2 describe-internet-gateways --profile "$AWS_USER" --region "$AWS_REGION" \
        --filters "Name=attachment.vpc-id,Values=${VPC_ID}" \
        --query 'InternetGateways[].InternetGatewayId' --output text --no-cli-pager 2>/dev/null || echo "")
    for IGW in $IGWS; do
        aws ec2 detach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$VPC_ID" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
        aws ec2 delete-internet-gateway --internet-gateway-id "$IGW" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
    done

    # Delete NAT gateways (block subnet deletion)
    NATS=$(aws ec2 describe-nat-gateways --profile "$AWS_USER" --region "$AWS_REGION" \
        --filter "Name=vpc-id,Values=${VPC_ID}" \
        --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text --no-cli-pager 2>/dev/null || echo "")
    for NAT in $NATS; do
        aws ec2 delete-nat-gateway --nat-gateway-id "$NAT" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
    done
    [ -n "$NATS" ] && { echo "    Waiting 60s for NAT gateways to delete..."; sleep 60; }

    # Release Elastic IPs that were attached to the NAT gateways
    EIPS=$(aws ec2 describe-addresses --profile "$AWS_USER" --region "$AWS_REGION" \
        --query "Addresses[?Tags[?Key==\`aws:cloudformation:stack-name\` && Value==\`${STACK_NAME}\`]].AllocationId" \
        --output text --no-cli-pager 2>/dev/null || echo "")
    for EIP in $EIPS; do
        aws ec2 release-address --allocation-id "$EIP" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
    done

    # Delete VPC endpoints
    VPCES=$(aws ec2 describe-vpc-endpoints --profile "$AWS_USER" --region "$AWS_REGION" \
        --filters "Name=vpc-id,Values=${VPC_ID}" \
        --query 'VpcEndpoints[].VpcEndpointId' --output text --no-cli-pager 2>/dev/null || echo "")
    if [ -n "$VPCES" ]; then
        aws ec2 delete-vpc-endpoints --vpc-endpoint-ids $VPCES \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
    fi

    # Release/await ENIs. Delete any 'available' ENIs; wait a bounded time for
    # 'in-use' ones (e.g. requester-managed OpenSearch/ELB ENIs) to detach.
    # Without this, subnet and VPC deletion fail with DependencyViolation.
    ENI_WAIT=0
    while [ $ENI_WAIT -lt 360 ]; do
        ENIS=$(aws ec2 describe-network-interfaces --profile "$AWS_USER" --region "$AWS_REGION" \
            --filters "Name=vpc-id,Values=${VPC_ID}" \
            --query 'NetworkInterfaces[].[NetworkInterfaceId,Status]' --output text --no-cli-pager 2>/dev/null || echo "")
        [ -z "$ENIS" ] && break
        # Delete available ENIs
        echo "$ENIS" | while read -r ENI_ID ENI_STATUS; do
            [ -z "$ENI_ID" ] && continue
            if [ "$ENI_STATUS" = "available" ]; then
                aws ec2 delete-network-interface --network-interface-id "$ENI_ID" \
                    --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
            fi
        done
        # Recount; if only in-use remain, wait for the owning service to release
        REMAIN=$(aws ec2 describe-network-interfaces --profile "$AWS_USER" --region "$AWS_REGION" \
            --filters "Name=vpc-id,Values=${VPC_ID}" \
            --query 'length(NetworkInterfaces)' --output text --no-cli-pager 2>/dev/null || echo "0")
        [ "$REMAIN" = "0" ] && break
        echo "    Waiting for $REMAIN ENI(s) to release... (${ENI_WAIT}s)"
        sleep 30
        ENI_WAIT=$((ENI_WAIT + 30))
    done

    # Delete subnets
    SUBNETS=$(aws ec2 describe-subnets --profile "$AWS_USER" --region "$AWS_REGION" \
        --filters "Name=vpc-id,Values=${VPC_ID}" \
        --query 'Subnets[].SubnetId' --output text --no-cli-pager 2>/dev/null || echo "")
    for SN in $SUBNETS; do
        aws ec2 delete-subnet --subnet-id "$SN" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
    done

    # Delete non-default route tables
    RTBS=$(aws ec2 describe-route-tables --profile "$AWS_USER" --region "$AWS_REGION" \
        --filters "Name=vpc-id,Values=${VPC_ID}" \
        --query 'RouteTables[?Associations[?Main!=`true`] || length(Associations)==`0`].RouteTableId' \
        --output text --no-cli-pager 2>/dev/null || echo "")
    for RT in $RTBS; do
        # Disassociate if needed, then delete
        ASSOCS=$(aws ec2 describe-route-tables --route-table-ids "$RT" \
            --profile "$AWS_USER" --region "$AWS_REGION" \
            --query 'RouteTables[0].Associations[?Main!=`true`].RouteTableAssociationId' \
            --output text --no-cli-pager 2>/dev/null || echo "")
        for A in $ASSOCS; do
            aws ec2 disassociate-route-table --association-id "$A" \
                --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
        done
        aws ec2 delete-route-table --route-table-id "$RT" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
    done

    # Delete non-default security groups
    SGS=$(aws ec2 describe-security-groups --profile "$AWS_USER" --region "$AWS_REGION" \
        --filters "Name=vpc-id,Values=${VPC_ID}" \
        --query 'SecurityGroups[?GroupName!=`default`].GroupId' \
        --output text --no-cli-pager 2>/dev/null || echo "")
    for SG in $SGS; do
        aws ec2 delete-security-group --group-id "$SG" \
            --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null || true
    done

    # Finally, delete the VPC (retry a few times for dependency lag)
    VPC_DELETED=0
    for vpc_attempt in 1 2 3 4 5; do
        if aws ec2 delete-vpc --vpc-id "$VPC_ID" \
                --profile "$AWS_USER" --region "$AWS_REGION" --no-cli-pager 2>/dev/null; then
            echo "    ✓ VPC $VPC_ID deleted"
            VPC_DELETED=1
            break
        fi
        sleep 15
    done
    if [ "$VPC_DELETED" -ne 1 ]; then
        echo "    ✗ VPC $VPC_ID could not be deleted after retries (dependencies remain)."
        echo "      Check remaining ENIs/subnets/SGs in the console for this VPC."
        CLEANUP_HAD_FAILURES=1
    fi
done
echo ""

echo "=========================================="
if [ "$CLEANUP_HAD_FAILURES" -ne 0 ]; then
    echo "⚠ Cleanup finished WITH FAILURES — see the ✗ lines above"
else
    echo "✓ Cleanup completed"
fi
echo "=========================================="
echo ""
echo "Summary:"
echo "  - SAM child stack (das-lambda-stack)"
echo "  - DAS S3 bucket (Object Lock retention removed)"
echo "  - RDS DeletionProtection disabled and waited"
echo "  - OSI pipeline + VPC endpoints"
echo "  - Main CloudFormation stack"
echo "  - SAM-managed bucket(s)"
echo "  - S3 Logging bucket"
echo "  - SAM-managed CloudFormation stack"
echo "  - Orphaned CloudWatch log groups"
echo "  - OpenSearchLogsPolicy resource policy"
echo "  - Bootstrap Secrets Manager secrets (Option 2 only)"
echo "  - CFT packaging bucket(s)"
echo "  - Orphaned KMS keys (scheduled for 7-day deletion)"
echo "  - Orphaned RDS clusters, subnet groups, instance profiles"
echo "  - Orphaned VPCs (with attached IGWs, NAT gateways, EIPs, endpoints, subnets, SGs)"
echo ""
echo "Note: DeletionProtection is re-enabled by default on next deploy."
echo ""
echo "If you used BootStrapFromCloudShell.sh (Option 2) to create an IAM user,"
echo "delete it now from CloudShell as the root/admin user:"
echo ""
echo "  USER_POLICY_ARN=\$(aws iam list-attached-user-policies --user-name $AWS_USER | jq -r '.AttachedPolicies[].PolicyArn')"
echo "  aws iam detach-user-policy --policy-arn \$USER_POLICY_ARN --user-name $AWS_USER"
echo "  ACCESS_KEY_ID=\$(aws iam list-access-keys --user-name $AWS_USER | jq -r '.AccessKeyMetadata[].AccessKeyId')"
echo "  aws iam delete-access-key --access-key-id \$ACCESS_KEY_ID --user-name $AWS_USER"
echo "  aws iam delete-user --user-name $AWS_USER"
echo ""

# Exit non-zero if any critical step failed, so callers/automation can detect it.
if [ "$CLEANUP_HAD_FAILURES" -ne 0 ]; then
    exit 1
fi
exit 0
