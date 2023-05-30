# 成本预估
您需要承担运行解决方案时使用亚马逊云科技各个服务的成本费用。


截至2023年5月，我们按照用户每天生成1000张图片，Dreambooth训练10次作为计算标准，在美国西部（俄勒冈）区域（us-west-2），使用此解决方案的估计成本为每月583美元。

|  服务  | 用量 | 费用/每月 | 
|  ----  | ----  | ----  |  
| AWS Lambda | 按照每天inference生成1000张图片，平均大概生成一张图片调用10次后端API， 总共300000次，平均每次lambda运行时间200ms，lambda的内存按照1024mb | $0.00 |
| Amazon API Gateway | 按照每天inference生成1000张图片，平均大概生成一张图片调用10次后端API， 总共300000次                            | $0.30         |
| Amazon Simple Storage Service (S3) |  1000GB | $23 |
| Amazon DynamoDB | 2GB存储 | $0.50 |
| Step Functions     |  部署endpoint和training使用到了step function， 按照600次调用step function，每个工作流平均15次的状态变化               | $0.13         |
| Amazon CloudWatch | 按照每月写入10GB的logs数据| $5.04 |
| Amazon Sagemaker Training |Storage (General Purpose SSD (gp2)), Instance name (ml.g4dn.2xlarge), Number of training jobs per month (300), Number of instances per job (1), Hour(s) per instance per job (1) | $282 |
| Amazon Sagemaker Inference(GPU) | Number of models per endpoint (1), Storage (General Purpose SSD (gp2)), Instance name (ml.g4dn.2xlarge), Number of instances per endpoint (1), Endpoint hour(s) per day (10), Endpoint day(s) per month (22), Number of models deployed (1) | $206 |
| Amazon Sagemaker Inference(CPU) | Number of models per endpoint (1), Storage (General Purpose SSD (gp2)), Instance name (ml.r5.xlarge), Number of models deployed (1), Number of instances per endpoint (1), Endpoint hour(s) per day (10), Endpoint day(s) per month (22) | $66 |
| 总计 |  | $583 |