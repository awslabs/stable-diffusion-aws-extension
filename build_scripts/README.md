# Version control for stable-diffusion-aws-extension

Update time: 20230727

| Supported Framework/Extension | Version No.| Update date | Commit ID |
| --------------------- | --------- | --------------------- | --------- |
| stable-diffusion-webui|1.5.1|20230727|68f336bd994bed5442ad95bad6b6ad5564a5409a|
| sd-webui-controlnet | v1.1.233|20230727|efda6ddfd82ebafc6e1150fbb7e1f27163482a82|
| sd_dreambooth_extension | 1.0.14| 20230708| c2a5617c587b812b5a408143ddfb18fc49234edf|
# How to play with /stable-diffusion-webui

```
accelerate launch --num_cpu_threads_per_process=6 launch.py --api

```

# How to build images


### Build public images for aigc endpoint for byoc which is used for GPU operations, like txt2img inference.

```
sh build_and_push.sh Dockerfile.aigc-endpoint-byoc.from_scratch aigc-endpoint-byoc

```

### Build public images for aigc endpoint for diffusers which is used for GPU operations, like txt2img inference.

```
sh build_and_push.sh Dockerfile.aigc-endpoint-diffusers.from_scratch aigc-endpoint-diffusers

```

### Build public images for aigc endpoint which is used for training model

```
sh build_and_push.sh Dockerfile.aigc-job.from_scratch aigc-job

```

### Update public ecr to your private ecr

```
sh update_private_ecr.sh aigc-endpoint-byoc|aigc-endpoint-diffusers|aigc-job

```
