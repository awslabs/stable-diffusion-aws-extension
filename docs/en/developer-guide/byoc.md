---
title: Custom Container
language_tabs:
 - shell: shell
language_clients:
 - shell: “”
toc_footers: []
Includes: []
HeadingLevel: 2

---

<!-- Generator: Widdershins v4.0.1 -->

<h1 id="stable-diffusion-train-and-deploy-api">Custom Container</h1>

# Overview

The **Extension for Stable Diffusion on AWS** is extremely flexible. You can replace the container image of the SageMaker Endpoint model at any time, or revert to the default image at any time.

To achieve this capability, follow these steps:

- Step 1: Build a Container Image
- Step 2: Prepare command execution environment and permissions
- Step 3: **Replace** the specified SageMaker Endpoint model image with your own‘s or **Restore** the default model image
- Step 4: Verify or diagnose whether the container image is work

<br>

# Build a Container Image

You can build your own container image and upload it to [Amazon ECR](https://console.aws.amazon.com/ecr){:target="_blank"} in the region where the solution is deployed, please read [Using Amazon ECR with the AWS CLI](https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html){:target="_blank"}
, after the operation is complete, you will get a ECR URI, such as:

```shell
123456789012.dkr. ecr.cn-northwest-1.amazonaws.com .cn/your-image:latest
```

Dockerfile template:

```dockerfile
# Use base iamge
FROM public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-inference

# Set environment variables to non-interactive (this prevents some prompts)
ENV DEBIAN_FRONTEND=non-interactive

# Install packages in a single RUN step
RUN apt-get install -y xxxxx && \
    apt-get clean && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

<br>

# Prepare command execution environment and permissions

There are two ways to execute the following commands:

**Method 1(Recommended)**：On [CloudShell](https://docs.aws.amazon.com/cloudshell/latest/userguide/welcome.html){:target="_blank"}，Please replace {region} with the region where the solution is deployed, such as: `us-east-1`
    - Login URL: https://{region}.console.aws.amazon.com/cloudshell/home
    - Please make sure that the account you logged in has sufficient permissions (such as the permission to deploy the solution), otherwise the command will fail due to insufficient permissions.
    - ![CloudShell](../../zh/images/CloudShell.png)
**Method 2**：To execute on your own environment, you need to:
    - Install [CURL](https://curl.se/){:target="_blank"}
    - Install [jq](https://jqlang.github.io/jq/){:target="_blank"}
    - Install and Configure [AWS CLI](https://docs.aws.amazon.com/zh_cn/cli/latest/userguide/cli-chap-getting-started.html){:target="_blank"}
    - Please make sure that the account you configured has sufficient permissions (such as the permission to deploy the solution), otherwise the command will fail due to insufficient permissions.

<br>

# Update container image

Once the ECR image is ready, you only need to replace the variables in the following command and execute to complete the image replacement:

- **{region}**: The region where the solution is deployed, such as: `us-east-1`
- **{endpoint-name}**: Endpoint name, such as: `infer-endpoint-111111`
- **{image-uri}**: container image URI

```shell
curl -s https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/build_scripts/update_endpoint_image.sh | bash -s {region} {endpoint-name} {image-uri}
```

<br>

# Restore the default image

To restore the default image, replace the variables in the following command and execute:

- **{region}**: The region where the solution is deployed, such as: `us-east-1`
- **{endpoint-name}**: Endpoint name, such as: `infer-endpoint-111111`

```shell
curl -s https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/build_scripts/update_endpoint_image.sh | bash -s {region} {endpoint-name} default
```

<br>

# Verify or diagnose whether the container image is work

After the container image is replaced, you can verify whether the container image is working properly by viewing the logs of the SageMaker Endpoint, or diagnose the cause of the problem:

- **{region}**: The region where the solution is deployed, such as: `us-east-1`
- **{endpoint-name}**: Endpoint name, such as: `infer-endpoint-111111`

```shell
https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups$3FlogGroupNameFilter$3D{endpoint-name}
```
