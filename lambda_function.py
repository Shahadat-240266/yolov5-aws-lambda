"""ICT5205 Assignment 2 - Image object identification (Amazon Rekognition).

API Gateway (POST /detect) -> Lambda -> Rekognition -> S3 (JSON) + DynamoDB.
Version 2: adds retries, structured logging and separate handling of write failures.
"""
import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Built-in retries: up to 5 attempts with exponential backoff and jitter.
RETRY_CONFIG = Config(retries={'max_attempts': 5, 'mode': 'standard'})

# Clients are created once per execution environment and reused by warm
# invocations. No request data is kept between invocations (stateless).
s3 = boto3.client('s3', config=RETRY_CONFIG)
rekognition = boto3.client('rekognition', config=RETRY_CONFIG)
dynamodb = boto3.resource('dynamodb', config=RETRY_CONFIG)

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['DYNAMODB_TABLE']
INPUT_PREFIX = 'input-images/'
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    request_id = getattr(context, 'aws_request_id', 'local')

    # 1. Parse and validate the request
    try:
        body = _parse_body(event)
    except (ValueError, TypeError):
        logger.warning('[%s] Request body is not valid JSON', request_id)
        return _response(400, {'error': 'Request body must be valid JSON'})

    image_key = body.get('image_key')
    if not isinstance(image_key, str) or not image_key.startswith(INPUT_PREFIX):
        logger.warning('[%s] Missing or invalid image_key: %r', request_id, image_key)
        return _response(400, {'error': "'image_key' is required and must start with 'input-images/'"})
    logger.info('[%s] Detecting labels for %s', request_id, image_key)

    # 2. Run object detection
    try:
        rek_response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': image_key}},
            MaxLabels=10,
            MinConfidence=70
        )
    except rekognition.exceptions.InvalidS3ObjectException:
        logger.warning('[%s] Image not found in S3: %s', request_id, image_key)
        return _response(404, {'error': f'Image not found in S3: {image_key}'})
    except ClientError:
        logger.exception('[%s] Rekognition call failed', request_id)
        return _response(500, {'error': 'Object detection failed'})

    labels = [
        {'name': label['Name'], 'confidence': round(label['Confidence'], 2)}
        for label in rek_response['Labels']
    ]
    image_id = image_key.split('/')[-1].replace('.', '_')
    timestamp = datetime.now(timezone.utc).isoformat()
    result_key = f'detection-results/{image_id}_{timestamp}.json'
    result = {
        'image_id': image_id,
        'timestamp': timestamp,
        'source_image': image_key,
        'detected_labels': labels
    }

    # 3. Store the result file in S3
    try:
        s3.put_object(Bucket=BUCKET_NAME, Key=result_key,
                      Body=json.dumps(result, indent=2),
                      ContentType='application/json')
    except ClientError:
        logger.exception('[%s] Failed to write %s to S3', request_id, result_key)
        return _response(500, {'error': 'Could not store the result file in S3'})

    # 4. Store the record in DynamoDB
    try:
        table.put_item(Item={
            'image_id': image_id, 'timestamp': timestamp,
            'source_image': image_key, 'result_s3_key': result_key,
            'detected_labels': json.dumps(labels)
        })
    except ClientError:
        logger.exception('[%s] Failed to write record for %s to DynamoDB', request_id, image_id)
        return _response(500, {'error': 'Could not store the record in DynamoDB'})

    logger.info('[%s] Stored %s (%d labels)', request_id, result_key, len(labels))
    return _response(200, {
        'message': 'Detection completed successfully',
        'image_id': image_id, 'timestamp': timestamp,
        'labels_detected': len(labels), 'detected_labels': labels,
        'result_s3_key': result_key
    })


def _parse_body(event):
    """Return the request body as a dict (API Gateway proxy or direct test event)."""
    body = event.get('body') if isinstance(event, dict) else None
    if body is None:
        body = event
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict):
        raise ValueError('JSON body must be an object')
    return body


def _response(status_code, body_dict):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body_dict)
    }
