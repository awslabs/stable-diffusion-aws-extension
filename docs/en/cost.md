# Cost

You are responsible for the cost of AWS services used when running this solution. 

As of June 2023, for example, based on generating 1000 images per day and training Dreambooth 10 times as the benchmark, the estimated cost of using this solution in the US West (Oregon) (us-west-2) is $583 per month.



|  Service  | Usage | Cost/Month | 
|  ----  | ----  | ----  |  
| AWS Lambda | Generate 1000 images per day for inference, and an average Lambda runtime of 200ms, with a memory size of 1024MB | $0.00 |
| Amazon API Gateway | Generate 1000 images per day for inference，with an average of approximately 10 backend API calls per image, totaling 300,000 calls                           | $0.30         |
| Amazon Simple Storage Service (S3) |  1000GB | $23 |
| Amazon DynamoDB | 2GB storage | $0.50 |
| Step Functions     |  Step function is used when deploying Amazon SageMaker Endpoint and model training， 600 calls of step function，on average 15 state changes per workflow               | $0.13         |
| Amazon CloudWatch | writing 10GB of log data per month | $5.04 |
| Amazon Sagemaker Training |Storage (General Purpose SSD (gp2)), Instance name (ml.g4dn.2xlarge), Number of training jobs per month (300), Number of instances per job (1), Hour(s) per instance per job (1) | $282 |
| Amazon Sagemaker Inference(GPU) | Number of models per endpoint (1), Storage (General Purpose SSD (gp2)), Instance name (ml.g4dn.2xlarge), Number of instances per endpoint (1), Endpoint hour(s) per day (10), Endpoint day(s) per month (22), Number of models deployed (1) | $206 |
| Amazon Sagemaker Inference(CPU) | Number of models per endpoint (1), Storage (General Purpose SSD (gp2)), Instance name (ml.r5.xlarge), Number of models deployed (1), Number of instances per endpoint (1), Endpoint hour(s) per day (10), Endpoint day(s) per month (22) | $66 |
| Total |  | $583 |

