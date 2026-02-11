variable "aws_region" {
    description = "AWS Region"
    type = string
    default = "us-east-1"
}
variable "project_name" {
    description = "Project name for resource naming"
    default = "event-pipeline"
}
variable "notification_email" {
    description = "Email for report notifications"
    type = string
}
