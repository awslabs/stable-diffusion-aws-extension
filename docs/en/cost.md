# Cost

You are responsible for the cost of AWS services used when running this solution. 

## Use auto-scale Amazon SageMaker Inference Endpoint for Image Inference
As of December 2023, for example, assuming that use will actively inference image for 8 hours per day, 20 working days per month(Assuming that using the standard Stable Diffusion XL model to generate a 1024 X 1024 image takes an average of 7 seconds. This running time can generate 72000 images in one month), the estimated cost of using this solution in the US East (Virginia)(us-east-1) is **$310.45** per month.

|  Service  | Usage | Cost/Month | 
|  ----  | ----  | ----  |  
| Amazon SageMaker | $276.00 | Number of models per endpoint (1), Storage (General Purpose SSD (gp2)), Instance name (ml.g5.2xlarge), Number of models deployed (1), Number of instances per endpoint (1), Endpoint hour(s) per day (8), Endpoint day(s) per month (20), Storage amount (240 GB per month) |
| AWS Lambda | $0.02 | Architecture (x86), Architecture (x86), Invoke Mode (Buffered), Amount of ephemeral storage allocated (10 GB), Number of requests (300000 per month), Concurrency (10) |
| Amazon API Gateway | $1.05 | REST API request units (thousands), Cache memory size (GB) (None), WebSocket message units (thousands), HTTP API requests units (thousands), Average message size (32 KB), Requests ( per month), Requests (300 per month)|
| Amazon Simple Storage Service (S3) | $27.70 | S3 Standard storage (1000 GB per month), PUT, COPY, POST, LIST requests to S3 Standard (), GET, SELECT, and all other requests from S3 Standard (1000000), Data returned by S3 Select (1000 GB per month) DT Inbound: All other regions (0 TB per month), DT Outbound: Internet (40 GB per month) |
| Amazon DynamoDB | $0.50 | Table class (Standard), Average item size (all attributes) (1 KB), Data storage size (2 GB) |
| AWS Step Functions | $0.13 | Workflow requests (600 per month), State transitions per workflow (15) |
| Amazon CloudWatch | $5.05 | Standard Logs: Data Ingested (10 GB) |
| Total | $310.45 ||


## Use Amazon SageMaker to Train Model
Assume that on the basis of inference images, users train for 300 hours per month as the calculation standard (fine-tuning a new safetensor model based on Stable Diffusion V1.5, 1000 steps of iteration, takes 387 seconds. 300 hours of training means one month of training **2790 models**), the estimated cost of using this solution would increase by **$526.18** in US East (N. Virginia) (us-east-1).

|  Service  | Usage | Cost/Month | 
|  ----  | ----  | ----  |  
| Amazon SageMaker | $526.18 | Storage (General Purpose SSD (gp2)), Instance name (ml.g5.2xlarge), Number of training jobs per month (300), Number of instances per job (1), Hour(s) per instance per job (1) |


