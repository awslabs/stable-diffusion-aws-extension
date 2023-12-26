# Version control for stable-diffusion-aws-extension

Update time: 20230926

| Supported Framework/Extension | Version No.| Commit ID |
| --------------------- | --------- |  --------- |
| stable-diffusion-webui|1.6.0|bda2ecdbf58fd33b4ad3036ed5cc13eef02747ae|
| sd-webui-controlnet | v1.1.410|7a4805c8ea3256a0eab3512280bd4f84ca0c8182|
| sd_dreambooth_extension | 1.0.14|cf086c536b141fc522ff11f6cffc8b7b12da04b9|
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
