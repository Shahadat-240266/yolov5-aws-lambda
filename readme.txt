ICT5205 Cloud Computing - Assignment 2 (Individual)
Name:           Md Shahadat Hossain
Student number: 240266

PROJECT
Serverless image object identification system on AWS.
A client uploads an image to Amazon S3 and sends a POST request (with an API key and
the S3 key of the image) to Amazon API Gateway. API Gateway calls an AWS Lambda
function, which reads the image from S3, detects objects with Amazon Rekognition
(DetectLabels), saves a JSON result file in S3 (detection-results/), stores the labels
in DynamoDB (table DetectionResults) and returns the labels to the client.

NOTE: Amazon Rekognition is used instead of YOLOv5 (see Section 2.1 of the report).

FOLDERS
code/    lambda_function.py   Lambda handler (version 2: retries, logging, validation)
         load_test.sh         Concurrency test for CloudShell (50 requests, 10 parallel)
deploy/  lambda_function.zip  Deployable Lambda package (handler: lambda_function.lambda_handler)
         iam_policy.json      Least-privilege IAM policy (replace <ACCOUNT_ID>)
images/  Figure_01 ... Figure_NN  All figures used in the report

DEPLOY (short version; full steps are in Section 5 of the report)
1. Create S3 bucket yolov5-detection-mshossain with folders input-images/ and detection-results/.
2. Create DynamoDB table DetectionResults (partition key image_id, sort key timestamp, On-Demand).
3. Create IAM role yolov5-detection-role (use deploy/iam_policy.json plus AWSLambdaBasicExecutionRole).
4. Create Lambda function (Python 3.12, 512 MB, 60 s), upload deploy/lambda_function.zip,
   set environment variables BUCKET_NAME and DYNAMODB_TABLE.
5. Create REST API with POST /detect (Lambda proxy integration), require an API key,
   create a usage plan and deploy to stage "prod".

LINKS (live URL, repository, YouTube video) are in Section 1 of the report.
