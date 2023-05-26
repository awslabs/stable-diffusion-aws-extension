# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


#FROM lambci/lambda:build-go1.x
FROM public.ecr.aws/sam/build-go1.x

USER root

RUN yum -y install \
    gpgme-devel \
    btrfs-progs-devel \
    device-mapper-devel \
    libassuan-devel \
    libudev-devel


WORKDIR /asset

COPY main ./