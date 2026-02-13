import json
import boto3
import os
from datetime import datetime, timedelta
from collections import Counter

s3 = boto3.client('s3')
sns = boto3.client('sns')

def lambda_handler(event, context):
    processed_bucket = os.environ['PROCESSED_BUCKET']
    report_bucket = os.environ['REPORT_BUCKET']
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']

    try: 
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')#calculate the date for yesterday and format it as a string in the format YYYY-MM-DD to filter processed files by date
        prefix = f"processed-data/{yesterday}/"

        print(f"Generating report for {yesterday}")
        
        response = s3.list_objects_v2(
            Bucket=processed_bucket, 
            Prefix=prefix
            )
        
        if 'Contents' not in response:
            print(f"No processed files found for {yesterday}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No data to report'})
            }
            
        
        total_records = 0
        total_files = 0
        all_data = []
        file_formats = Counter()

        for obj in response['Contents']:#iterate through the list of processed files for yesterday and read their content to aggregate data and generate the report
            print(f"  Reading: {obj['Key']}")
            file_response = s3.get_object(
                Bucket=processed_bucket, 
                Key=obj['Key']
                )
            file_data = json.loads(file_response['Body'].read().decode('utf-8'))#read the content of the file, decode it from bytes to string, and parse it as JSON to extract the processed data and metadata for aggregation and analysis in the report

            total_files += 1
            total_records += file_data.get('record_count', 0)
            
            source_format = file_data.get('source_format', 'unknown')
            file_formats[source_format] += 1

            data=file_data.get('data', [])
            
            if isinstance(data, list):
                all_data.extend(data)#if the data is a list of records, extend the all_data list with the records; if it's a single record (dictionary), append it to the all_data list to ensure all records are aggregated for analysis in the report
            else:
                all_data.append(data)

        event_types = Counter()
        user_actions = Counter()
        total_amount = 0

        for record in all_data: #iterate through all the aggregated records and analyze specific fields such as event types, user actions, and transaction amounts to generate insights for the report
            if isinstance(record, dict):
                event_type = record.get('event_type')
                if event_type:
                    event_types[event_type] += 1

                user_action = record.get('user_action')
                if user_action:
                    user_actions[user_action] += 1

                amount = record.get('amount')
                try:
                    if isinstance(amount, (float)):
                        total_amount += amount
                except (ValueError, TypeError):
                    pass

        summary = { #create a summary dictionary to store the report data, including metadata about the report generation and the results of the data analysis for easy reference and sharing in the report
            'report_date': yesterday,
            'generated_at': datetime.now().isoformat(),
            'processing_summary': {
                'total_files_processed': total_files,
                'total_records': total_records,
                'file_formats': dict(file_formats)
            },
            'data_analysis': {
                'event_types': dict(event_types),
                'user_actions': dict(user_actions),
                'total_amount': round(total_amount, 2)
            },
            'sample_records': all_data[:5]  # First 5 records
        }

        report_key = f"daily_reports/{yesterday}-summary.json" #define the key for the report file in the report bucket
        
        s3.put_object(
            Bucket=report_bucket, 
            Key=report_key, 
            Body=json.dumps(summary, indent=2).encode('utf-8'),
            ContentType='application/json'
            ) 
        print(f"Report saved to s3://{report_bucket}/{report_key}")
        
        # Generate a simple text report for email notification
        text_report = f""" 
Daily Data Processing Report
{'=' * 50}
Date: {yesterday}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PROCESSING SUMMARY
{'-' * 50}
Files Processed: {total_files}
Total Records: {total_records}
File Formats: {', '.join([f'{fmt}={count}' for fmt, count in file_formats.items()])}

DATA ANALYSIS
{'-' * 50}
Event Types:
{chr(10).join([f'  - {event}: {count}' for event, count in event_types.items()])}

User Actions:
{chr(10).join([f'  - {action}: {count}' for action, count in user_actions.items()])}

Total Transaction Amount: ${total_amount:,.2f}

REPORT LOCATION
{'-' * 50}
S3 Path: s3://{report_bucket}/{report_key}
        """

        text_report_key = f"daily_reports/{yesterday}-summary.txt"
        s3.put_object(
            Bucket=report_bucket, 
            Key=text_report_key, 
            Body=text_report.encode('utf-8'),
            ContentType='text/plain'
        )
        print(f"Text report saved to s3://{report_bucket}/{text_report_key}")

        email_subject = f"Daily Data Processing Report - {yesterday}"
        email_body = text_report + f"\n\nView full report:\nJSON: s3://{report_bucket}/{report_key}\nText: s3://{report_bucket}/{text_report_key}"

        sns.publish(#send an email notification with the report summary and links to the full report in both JSON and text formats for easy access and review by stakeholders
            TopicArn=sns_topic_arn,
            Subject=email_subject,
            Message=email_body
        )
        print(f"email notification sent to SNS topic: {sns_topic_arn}")

        return {
            'statusCode': 200,
            'body': json.dumps(summary)
        }


    except Exception as e:
        print(f"Error generating report: {str(e)}")

        try:#if an error occurs during the report generation process, attempt to send an email notification with the error details to alert stakeholders of the issue for timely investigation and resolution
            sns.publish(
                TopicArn=sns_topic_arn,
                Subject=f"Error Generating Daily Report - {datetime.now().strftime('%Y-%m-%d')}",
                Message=f"An error occurred while generating the daily report:\n\n{str(e)}"
            )
        except:
            pass
        raise
        