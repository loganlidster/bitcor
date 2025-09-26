# Bitcor Infra (us-west-1) — Starter

This repo provisions AWS infrastructure from GitHub Actions using OIDC (no keys). Region: **us-west-1**.

## 1) Create IAM role + Terraform state (CloudFormation)
AWS Console → **us-west-1** → CloudFormation → *Create stack (with new resources)* → Upload `infra/cloudformation/github-oidc-role.yaml`.

Parameters:
- GitHubOrg: `loganlidster`
- RepoName: `bitcor`
- RoleName: `GitHubDeployRole`
- BranchName: `main`
- TfStateBucketName: `bitcor-tfstate-546929127780-usw1`
- TfStateLockTableName: `tf-state-lock-table`

Wait for **CREATE_COMPLETE**, then copy Outputs:
- DeployRoleArn
- TfStateBucketOut
- TfStateLockTableOut

## 2) Add GitHub repository variables (Settings → Secrets and variables → Actions → Variables)
- `AWS_ACCOUNT_ID` = `546929127780`
- `AWS_REGION` = `us-west-1`
- `AWS_DEPLOY_ROLE` = `GitHubDeployRole`
- `TF_STATE_BUCKET` = `bitcor-tfstate-546929127780-usw1`
- `TF_STATE_LOCK_TABLE` = `tf-state-lock-table`

## 3) Run the workflow
GitHub → **Actions → infra → Run workflow** (branch `main`).

### What gets created
- ECR repos: `v7-api`, `v7-engine`
- ECS cluster: `bitcor-cluster`
- VPC: 2 public + 2 private subnets, IGW, 1 NAT, route tables, SGs (ALB/ECS/RDS)
