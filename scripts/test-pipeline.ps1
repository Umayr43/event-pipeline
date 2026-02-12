# Test Pipeline Script for Windows

Write-Host "=== Event Pipeline Test Script ===" -ForegroundColor Green

# Move to terraform directory
Set-Location -Path "$PSScriptRoot\..\terraform"

# Get bucket names
Write-Host "`nGetting bucket names..." -ForegroundColor Yellow
$INPUT_BUCKET = terraform output -raw input_bucket
$PROCESSED_BUCKET = terraform output -raw processed_bucket
$REPORT_BUCKET = terraform output -raw report_bucket

Write-Host "Input Bucket: $INPUT_BUCKET" -ForegroundColor Cyan
Write-Host "Processed Bucket: $PROCESSED_BUCKET" -ForegroundColor Cyan
Write-Host "Report Bucket: $REPORT_BUCKET" -ForegroundColor Cyan

# Get Lambda function names
Write-Host "`nGetting Lambda function names..." -ForegroundColor Yellow
$PROCESSOR = aws lambda list-functions --query "Functions[?contains(FunctionName, 'processor')].FunctionName" --output text
$REPORTER = aws lambda list-functions --query "Functions[?contains(FunctionName, 'generator')].FunctionName" --output text

Write-Host "Processor: $PROCESSOR" -ForegroundColor Cyan
Write-Host "Reporter: $REPORTER" -ForegroundColor Cyan

# Upload test file
Write-Host "`nUploading test file..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\.."
aws s3 cp sample_data\csv_test_events.csv s3://$INPUT_BUCKET/

# Wait and check logs
Write-Host "`nWaiting 10 seconds for processing..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "`nChecking Lambda logs..." -ForegroundColor Yellow
aws logs tail /aws/lambda/$PROCESSOR --since 2m

# Check processed files
Write-Host "`nListing processed files..." -ForegroundColor Yellow
$TODAY = Get-Date -Format "yyyy-MM-dd"
aws s3 ls s3://$PROCESSED_BUCKET/processed-data/$TODAY/

Write-Host "`n=== Test Complete ===" -ForegroundColor Green
Write-Host "Check your email for the daily report!" -ForegroundColor Yellow
