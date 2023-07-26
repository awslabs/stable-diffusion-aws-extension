# Version control for stable-diffusion-aws-extension

Update time: 20230726

| Supported Framework/Extension | Version No.| Update date | Commit ID |
| --------------------- | --------- | --------------------- | --------- |
| stable-diffusion-webui|1.5.0|20230725|a3ddf464a2ed24c999f67ddfef7969f8291567be|
| sd-webui-controlnet | v1.1.233|20230715|e9679f8fc50880a92d6f1b6fc1aabad41079efd5|
| sd_dreambooth_extension | 1.0.14| 20230708| c2a5617c587b812b5a408143ddfb18fc49234edf|
| sd-webui-segment-anything | - | 20230626 | ffe263155d7f3ac4ee23a96262ecb77b9899ed95 | 
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
