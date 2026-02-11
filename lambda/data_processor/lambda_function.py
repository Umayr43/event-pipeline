import json
import boto3 #AWS SDK for Python, used to interact with AWS services like S3
import os #used to access environment variables, such as the name of the processed bucket
import csv
from datetime import datetime
import urllib.parse
from io import StringIO

s3 = boto3.client('s3')

def csv_to_json(csv_content):
    csv_file = StringIO(csv_content) #treat the string as a file-like object
    csv_reader = csv.DictReader(csv_file) #create a DictReader to read the CSV content as dictionaries

    data=[] 
    for row in csv_reader: 
        cleaned_row={}  #create an empty dictionary to store the cleaned row
        for key, value in row.items():
            if value:#check if the value is not empty

                try:
                    cleaned_row[key] = float(value)if '.' in value else int(value)
                except ValueError:
                    cleaned_row[key] = value
        data.append(cleaned_row)
    return data




def lambda_handler(event, context):
    processed_bucket = os.environ['PROCESSED_BUCKET']
    try:
        source_bucket = event['Records'][0]['s3']['bucket']['name'] #get the name of the source bucket from the event
        source_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key']) #get the key of the source object from the event and decode it
        file_extension = source_key.split('.')[-1].lower()

        print(f"Processing {file_extension.upper()} file: s3://{source_bucket}/{source_key}")
        response = s3.get_object(Bucket=source_bucket, Key=source_key)
        content = response['Body'].read().decode('utf-8') #read the content of the file and decode it from bytes to string

        if file_extension == 'csv':
            print("Converting CSV to JSON...")
            data = csv_to_json(content)
            source_format='csv'
        elif file_extension == 'json':
            print("Validating JSON format...")
            data = json.loads(content)  #parse the JSON content into a Python object (list or dictionary)
            source_format='json'
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        if not isinstance(data, list):
            data = [data] #ensure that the data is always a list, even if it's a single JSON object, to maintain consistency in processing and storage

        processed_data = {                  #create a dictionary to store the processed data and metadata
            "source_bucket": source_bucket,
            "source_key": source_key,
            "source_format": source_format,
            "processed_timestamp": datetime.now().isoformat(),
            "record_count": len(data),
            "data": data
        }

        today = datetime.now().strftime('%Y-%m-%d') #format the current date as a string in the format YYYY-MM-DD to organize processed files by date

        output_filename = source_key.replace(f'.{file_extension}', '.json')
        output_key = f"processed-data/{today}/{output_filename}"

        s3.put_object(
            Bucket=processed_bucket, 
            Key=output_key, 
            Body=json.dumps(processed_data),
            ContentType='application/json'
        )

        print(f"Converted {source_format.upper()} to JSON")
        print(f"Record count: {len(data)}")
        print(f"Successfully processed and uploaded: s3://{processed_bucket}/{output_key}")
        
        return { #return a response indicating the success of the operation, including details about the processed file and the output location
            'statusCode': 200, 
            'body': json.dumps({
                'message': f'Successfully processed and uploaded: s3://{processed_bucket}/{output_key}',
                'output_key': output_key,
                'record_count': len(data),
                'formats_conversion': f'{source_format.upper()} to JSON'
            })
        }

    except Exception as e:
        print(f"Error fetching file from S3: {e}")
        raise