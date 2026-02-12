# Event Pipeline - Windows Setup Guide

## Prerequisites

- Windows 10/11
- PowerShell 7+ (recommended)
- AWS CLI installed
- Terraform installed
- Git installed

## Quick Start

### 1. Deploy Infrastructure
```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

### 2. Test with Sample Data
```powershell
# Get bucket name
$BUCKET = terraform output -raw input_bucket

# Upload test file
aws s3 cp ..\sample_data\csv_test_events.csv s3://$BUCKET/
```

### 3. Check Logs
```powershell
# Get function name
$FUNCTION = aws lambda list-functions --query "Functions[?contains(FunctionName, 'processor')].FunctionName" --output text

# View logs
aws logs tail /aws/lambda/$FUNCTION --follow
```

## Troubleshooting

### PowerShell Execution Policy
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### AWS CLI Not Found
```powershell
# Check installation
aws --version

# Add to PATH if needed
$env:Path += ";C:\Program Files\Amazon\AWSCLIV2"
```

## Daily Operations

Upload new data:
```powershell
aws s3 cp your-data.csv s3://YOUR-INPUT-BUCKET/
```

View reports:
```powershell
aws s3 ls s3://YOUR-REPORTS-BUCKET/daily-reports/
```
