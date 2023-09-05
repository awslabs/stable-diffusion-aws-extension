# Version control for stable-diffusion-aws-extension

Update time: 20230727

| Supported Framework/Extension | Version No.| Update date | Commit ID |
| --------------------- | --------- | --------------------- | --------- |
| stable-diffusion-webui|1.6.0|20230901|5ef669de080814067961f28357256e8fe27544f4|
| sd-webui-controlnet | v1.1.401|20230905|fd37e9fc7ced2c3a39aaa3860916672c8d0fbfe8|
| sd_dreambooth_extension | 1.0.14| 20230708| c2a5617c587b812b5a408143ddfb18fc49234edf|
| multidiffusion-upscaler-for-automatic111 | - | 20230722 |
f9f8073e64f4e682838f255215039ba7884553bf|
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
