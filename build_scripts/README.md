# Vesion control for stable-diffusion-aws-extension

Update time: 20230605

| Supported Framework/Extension | Version No.| Update date | Commit ID |
| --------------------- | --------- | --------------------- | --------- |
| stable-diffusion-webui|1.3.1|20230602| b6af0a3809ea869fb180633f9affcae4b199ffcf |
| sd-webui-controlnet | v1.1.216| 20230605| f36493878b299c367bc51f2935fd7e6d19188569 |
| sd_dreambooth_extension | 1.0.14| 20230604| b396af26b7906aa82a29d8847e756396cb2c28fb |

# How to play with /stable-diffusion-webui

```
accelerate launch --num_cpu_threads_per_process=6 launch.py --api

```

# How to build images

### Build public images for aigc-webui-utils which is used for light-weight CPU operations, like create_model in Dreambooth, merge_checkpoint.

```
sh build_and_push.sh Dockerfile.utils.from_scratch aigc-webui-utils

```

### Build public images for aigc-webui-inference which is used for GPU operations, like txt2img inference.

```
sh build_and_push.sh Dockerfile.inference.from_scratch aigc-webui-inference

```

### Build public images for aigc-webui-dreambooth-train which is used for training model in Dreambooth.

```
sh build_and_push.sh Dockerfile.dreambooth.from_scratch aigc-webui-dreambooth-training

```

### Update public ecr to your private ecr

```
sh update_private_ecr.sh aigc-webui-utils|aigc-webui-inference|aigc-webui-dreambooth-training

```
