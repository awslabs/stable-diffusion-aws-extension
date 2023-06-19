# Vesion control for stable-diffusion-aws-extension

Update time: 20230619

| Supported Framework/Extension | Version No.| Update date | Commit ID |
| --------------------- | --------- | --------------------- | --------- |
| stable-diffusion-webui|1.3.2|20230605|baf6946e06249c5af9851c60171692c44ef633e0 |
| sd-webui-controlnet | v1.1.217|20230619| 5fc952793aa97bdd0078574b3be8bc98e1fcf2cd |
| sd_dreambooth_extension | 1.0.14| 20230606| dc413a14379b165355502d9f65856c40a4bb5b6f|

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
