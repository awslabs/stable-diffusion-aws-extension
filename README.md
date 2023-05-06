# Stable Diffusion AWS Extensions

## Introduction

An extension of Stable Diffusion web UI, that aims to help customers quickly and conveniently utilize the powerful features of Amazon SageMaker for AIGC-related inference and training tasks, without worrying about performance bottlenecks and engineering issues such as request load balancing that may arise from single-machine deployment.

As this solution is installed via an open source community plugin, users do not need to change their current user behavior or learn a new user interface platform, thus improving the user experience. At the same time, the non-intrusive code modification of this plugin helps users quickly catch up with the iterative community-related features. The supported features can be found [here](https://github.com/aws-samples/stable-diffusion-aws-extension/edit/main/README.md#features-supported).


## Features Supported
- txt2img
- Dreambooth VXXX
- ControlNet Vxxx
- LoRa Vxxx

## Installation


## Documentation
 The implementation guide can be found [here]().


## For contributor
Setup your repo first:

```bash
# clone original repo
git clone https://github.com/awslabs/aws-ai-solution-kit.git

# checkout to aigc branch
git checkout aigc

# goto applications/stable-diffusion-extensions folder and develop on aigc branch
git add .
git commit -m "commit message"
git push origin aigc
```

### Extensions module
Install dependencies, add all new dependencies to requirements.txt:

```bash
pip install -r requirements.txt
```

### Middleware module
Deploy stack with command:

```bash
npx cdk deploy --require-approval never
```



