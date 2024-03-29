# Version control for stable-diffusion-aws-extension

Update time: 20240118

| Supported Framework/Extension | Version No.| Commit ID |
| --------------------- | --------- |  --------- |
| stable-diffusion-webui|1.8.0|bef51aed032c0aaa5cfd80445bc4cf0d85b408b5|
| sd-webui-controlnet | v1.1.410|7a4805c8ea3256a0eab3512280bd4f84ca0c8182|
| Tiled Diffusion & VAE | |f9f8073e64f4e682838f255215039ba7884553bf|
| rembg | |3d9eedbbf0d585207f97d5b21e42f32c0042df70|
| Reactor | 0.6.1|0185d7a2afa4a3c76b304314233a1cafd1cf4842|

# How to play with /stable-diffusion-webui

```
accelerate launch --num_cpu_threads_per_process=6 launch.py --api

```

# How to build images

### Build public images for aigc-webui-utils which is used for light-weight CPU operations, like create_model in merge_checkpoint.

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
sh update_private_ecr.sh aigc-webui-utils|aigc-webui-inference

```
