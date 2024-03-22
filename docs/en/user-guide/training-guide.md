# Training Guide


The training is based on [Kohya-SS](https://github.com/kohya-ss/sd-scripts). Kohya-SS is a Python library for finetuning stable diffusion model which is friendly for consumer-grade GPU and compatible with the Stable Diffusion WebUI. The solution can do LoRA training both on SDXL and SD 1.5.

## Training User Guide

### Prepare Foundation Model

Upload your local SD model to S3 bucket by following commands
```
# Configure credentials
aws configure
# Copy local SD model to S3 bucket
aws s3 cp *safetensors s3://<bucket_path>/<model_path>
```

### Prepare Dataset

Execute AWS CLI command to copy the dataset to S3 bucket
```
aws s3 sync local_folder_name s3://<bucket_name>/<folder_name>
```

The folder name should be started with a number and underline, eg. 100_demo. Each image should be paired with a txt file with the same name, eg. demo1.png, demo1.txt, the demo1.txt contains the captions of demo1.png.

### Invoke Training API

Refer to [API document](https://awslabs.github.io/stable-diffusion-aws-extension/en/developer-guide/api/1.5.0/) to invoke training API.
