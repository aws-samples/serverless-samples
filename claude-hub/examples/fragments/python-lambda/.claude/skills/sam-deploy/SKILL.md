# SAM Deploy

Deploys the SAM application to AWS. Runs build, validation, and deploy steps in sequence.

## Steps

1. **Validate the template**
   ```bash
   sam validate --lint
   ```
   Fix any validation errors before proceeding.

2. **Build the application**
   ```bash
   sam build
   ```
   If the build fails due to Python version mismatch, retry with:
   ```bash
   sam build --use-container
   ```

3. **Check for YAML issues**
   Verify no duplicate keys were introduced by automated edits:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('template.yaml'))"
   ```

4. **Deploy**
   For standard (non-production) deploys:
   ```bash
   sam deploy
   ```
   This uses settings from `samconfig.toml`. Ensure `confirm_changeset = false` for automated deploys.

   For first-time or guided deploys:
   ```bash
   sam deploy --guided
   ```

5. **Verify deployment**
   Check the CloudFormation stack status:
   ```bash
   aws cloudformation describe-stacks --stack-name <STACK_NAME> --query 'Stacks[0].StackStatus'
   ```

## Troubleshooting

- **First deploy KMS/CreateGrant failure**: Delete the failed stack with `sam delete` and redeploy.
- **Multiple GSI changes**: CloudFormation only supports adding/removing one GSI per update. Delete and redeploy if multiple GSI changes are needed.
- **Build errors**: Check that the Python version on PATH matches the runtime specified in `template.yaml`.

## Post-Deploy

- Run seed scripts if this is a fresh deployment: `bash scripts/seed.sh` (if present).
- Check CloudWatch Logs for any startup errors in the deployed functions.
