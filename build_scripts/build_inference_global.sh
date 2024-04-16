#!/usr/bin/env bash

aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 366590864501.dkr.ecr.us-east-2.amazonaws.com
docker tag 753680513547.dkr.ecr.cn-north-1.amazonaws.com.cn/esd-inference:sd-v1.5.0-63ed65c 366590864501.dkr.ecr.us-east-2.amazonaws.com/esd-inference:v1.5.0-63ed65c
docker push 366590864501.dkr.ecr.us-east-2.amazonaws.com/esd-inference:v1.5.0-63ed65c

aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 366590864501.dkr.ecr.us-west-2.amazonaws.com
docker tag 753680513547.dkr.ecr.cn-north-1.amazonaws.com.cn/esd-inference:sd-v1.5.0-63ed65c 366590864501.dkr.ecr.us-west-2.amazonaws.com/esd-inference:v1.5.0-63ed65c
docker push 366590864501.dkr.ecr.us-west-2.amazonaws.com/esd-inference:v1.5.0-63ed65c

aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin 366590864501.dkr.ecr.ap-southeast-1.amazonaws.com
docker tag 753680513547.dkr.ecr.cn-north-1.amazonaws.com.cn/esd-inference:sd-v1.5.0-63ed65c 366590864501.dkr.ecr.ap-southeast-1.amazonaws.com/esd-inference:v1.5.0-63ed65c
docker push 366590864501.dkr.ecr.ap-southeast-1.amazonaws.com/esd-inference:v1.5.0-63ed65c


aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 366590864501.dkr.ecr.us-east-1.amazonaws.com
docker tag 753680513547.dkr.ecr.cn-north-1.amazonaws.com.cn/esd-inference:sd-v1.5.0-63ed65c 366590864501.dkr.ecr.us-east-1.amazonaws.com/esd-inference:v1.5.0-63ed65c
docker push 366590864501.dkr.ecr.us-east-1.amazonaws.com/esd-inference:v1.5.0-63ed65c

aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin 366590864501.dkr.ecr.ap-northeast-1.amazonaws.com
docker tag 753680513547.dkr.ecr.cn-north-1.amazonaws.com.cn/esd-inference:sd-v1.5.0-63ed65c 366590864501.dkr.ecr.ap-northeast-1.amazonaws.com/esd-inference:v1.5.0-63ed65c
docker push 366590864501.dkr.ecr.ap-northeast-1.amazonaws.com/esd-inference:v1.5.0-63ed65c