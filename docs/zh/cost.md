# 成本预估
您需要承担运行解决方案时使用亚马逊云科技各个服务的成本费用。

## 使用自动弹性伸缩的Amazon SageMaker Endpoint做图片推理
截至2023年12月，我们按照用户每天使用解决方案推理图片8小时，每月运行20个工作日为计算标准（以使用标准Stable Diffusion XL模型生成一张1024*1024的图，平均需要7秒为例，此运行时间一个月能生成72000张图），使用此解决方案的预估成本在美国东部（弗吉尼亚北部）（us-east-1）为每月**416.85美元**。

|  服务  | 用量 | 费用/每月 | 
|  ----  | ----  | ----  |  
| Amazon SageMaker | $276.00 | 一个月运行20个工作日，每天8小时，存储General Purpose SSD (gp2)，存储数量240 GB/月，实例类型ml.g5.2xlarge，部署1个模型，1个实例数量 |
| AWS Lambda | $0.02 | Architecture (x86), Architecture (x86), 调用模式（Buffered），分配的临时存储量（10 GB）, 请求数量300000次/月，并发10 |
| Amazon API Gateway | $1.05 | REST API请求单位（千），缓存内存大小 (GB)（无），WebSocket 消息单位（千），HTTP API 请求单位（千），平均消息大小 (32 KB)，请求（300/月）|
| Amazon Simple Storage Service (S3) | $27.70 | 假设一张图500KB，读取10000张图/月；选择S3标准存储（1000 GB/月），对S3 Standard的 PUT、COPY、POST、LIST 请求，GET、SELECT以及来自S3 Standard的所有其他请求（1000000），S3 Select返回的数据（1000 GB/月），DT 入站：所有其他区域（0 TB/月），DT 出站：互联网（40 GB月） |
| Amazon DynamoDB | $0.50 | 表类（标准），平均项目大小（所有属性）(1 KB)，数据存储大小 (2 GB) |
| AWS Step Functions | $0.13 | 工作流请求 600/月，每个工作流程的状态转换（15） |
| Amazon CloudWatch | $5.05 | 标准日志：数据注入（10GB） |
| 总计| $310.45 ||


## 使用Amazon SageMaker模型训练
假设在推理图片基础上，以用户每个月训练300小时为计算标准（使用Dreambooth，基于Stable Diffusion微调一个新的safetensor模型，1000步迭代，需要387秒。300小时的训练意味着一个月训练了**2790**个模型），使用此解决方案的预估成本在美国东部（弗吉尼亚北部）（us-east-1）会增加**526.18美元**。

|  服务  | 用量 | 费用/每月 | 
|  ----  | ----  | ----  |  
| Amazon SageMaker | $526.18 | 存储（通用 SSD (gp2)），实例名称 (ml.g5.2xlarge)，每月训练作业数 (300)，每个作业的实例数 (1)，每个作业每个实例的小时数 (1) |
| 总计| $526.18 ||


