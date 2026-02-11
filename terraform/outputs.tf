output "input_bucket" {
    value = aws_s3_bucket.input_bucket.id
}
output "processed_bucket" {
    value = aws_s3_bucket.processed_bucket.id
}
output "report_bucket" {
    value = aws_s3_bucket.report_bucket.id
}