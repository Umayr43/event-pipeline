output "input_bucket" {
    value = aws_s3_bucket.input_bucket.bucket
}
output "processed_bucket" {
    value = aws_s3_bucket.processed_bucket.bucket
}
output "report_bucket" {
    value = aws_s3_bucket.report_bucket.bucket
}