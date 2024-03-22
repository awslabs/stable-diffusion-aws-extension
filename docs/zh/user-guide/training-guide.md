# 训练指南

训练基于[Kohya-SS](https://github.com/kohya-ss/sd-scripts)。 Kohya-SS是一个Python库，用于微调稳定扩散模型，适用于消费级GPU，并兼容稳定扩散WebUI。该解决方案可以在SDXL和SD 1.5上进行LoRA训练。

## 训练用户指南

### 准备基础模型

通过以下命令将本地SD模型上传到S3存储桶
```
# 配置凭证
aws configure
# 将本地SD模型复制到S3存储桶
aws s3 cp *safetensors s3://<bucket_path>/<model_path>
```

### 准备数据集

执行AWS CLI命令将数据集复制到S3存储桶
```
aws s3 sync local_folder_name s3://<bucket_name>/<folder_name>
```

文件夹名称应以数字和下划线开头，例如100_demo。每个图像应与具有相同名称的txt文件配对，例如demo1.png，demo1.txt，demo1.txt包含demo1.png的标题。

### 调用训练API

参考[API文档](https://awslabs.github.io/stable-diffusion-aws-extension/zh/developer-guide/api/1.5.0/)调用训练API。
