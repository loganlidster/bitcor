# Bitcor Infra (us-west-1)

This repo provisions AWS infrastructure from GitHub Actions without access keys (OIDC). Region is **us-west-1**.

## Step 1 — Create IAM role + Terraform state

AWS Console → **us-west-1** → CloudFormation → *Create stack (with new resources)* → Upload `infra/cloudformation/github-oidc-role.yaml`.

Parameters:
- **GitHubOrg**: `<your GitHub username>` (e.g., `loganlidster`)
- **RepoName**: `bitcor`
- **RoleName**: `GitHubDeployRole` (or your preferred name)
- **BranchName**: `main`
- **TfStateBucketName**: `bitcor-tfstate-<random>` (must be globally unique)
- **TfStateLockTableName**: `tf-state-lock-table`
- **CreateOidcProvider**: `true` (set to `false` only if you already have an OIDC provider)
- **ExistingOidcProviderArn**: *(leave blank unless CreateOidcProvider=false)*

Wait for **CREATE_COMPLETE** → go to **Outputs** and copy:
- `DeployRoleArn`
- `TfStateBucketOut`
- `TfStateLockTableOut`

## Step 2 — Add GitHub repository variables

Repo → **Settings → Secrets and variables → Actions → Variables** → add these (exact names):

- `AWS_ACCOUNT_ID` = *your 12‑digit AWS account id*
- `AWS_REGION` = `us-west-1`
- `AWS_DEPLOY_ROLE` = `GitHubDeployRole` (or your chosen RoleName)
- `TF_STATE_BUCKET` = *(value from `TfStateBucketOut`)*
- `TF_STATE_LOCK_TABLE` = *(value from `TfStateLockTableOut`)*

> Use **Variables**, not Secrets.

## Step 3 — Apply Infra from Actions

GitHub → **Actions → infra → Run workflow** (branch `main`).

On success you’ll see in AWS (region **us-west-1**):
- **ECR** repos: `v7-api`, `v7-engine`
- **ECS** cluster: `bitcor-cluster`
