#!/usr/bin/env bash
set -euxo pipefail

title() {
    echo "------------------------------------------------------------------------------"
    echo $*
    echo "------------------------------------------------------------------------------"
}

run() {
    >&2 echo "[run] $*"
    $*
}

__dir="$(cd "$(dirname $0)";pwd)"
SRC_PATH="${__dir}/../infrastructure/src"

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Parameters not enough"
    echo "Example: $(basename $0) <BUCKET_NAME> <SOLUTION_NAME> [VERSION]"
    exit 1
fi

export BUCKET_NAME=$1
export SOLUTION_NAME=$2
export BUILD_VERSION=$3
export GLOBAL_S3_ASSETS_PATH="${__dir}/global-s3-assets"

title "init env"

run rm -rf ${GLOBAL_S3_ASSETS_PATH} && run mkdir -p ${GLOBAL_S3_ASSETS_PATH}

echo "BUCKET_NAME=${BUCKET_NAME}"
echo "SOLUTION_NAME=${SOLUTION_NAME}"
echo "e=${BUILD_VERSION}"
echo "${BUILD_VERSION}" > ${GLOBAL_S3_ASSETS_PATH}/version

title "cdk synth"

run cd ${SRC_PATH}
run npm install 
# if [ "$BUILD_VERSION" != 'latest' ]; then
# sed -i "1,210s/\"version\":.*$/\"version\": \"$BUILD_VERSION\",/g" package.json
# fi

export USE_BSS=true
# see https://github.com/aws-samples/cdk-bootstrapless-synthesizer/blob/main/API.md for how to config
export BSS_TEMPLATE_BUCKET_NAME="${BUCKET_NAME}"
export BSS_FILE_ASSET_BUCKET_NAME="${BUCKET_NAME}-\${AWS::Region}"
export FILE_ASSET_PREFIX="${SOLUTION_NAME}/${BUILD_VERSION}/"

# container support
export BSS_IMAGE_ASSET_TAG_PREFIX="${BUILD_VERSION}"
export BSS_IMAGE_ASSET_TAG_SUFFIX_TYPE=NONE
# export BSS_IMAGE_ASSET_TAG_PREFIX=""

#export BSS_IMAGE_ASSET_ACCOUNT_ID=${AWS_CN_ASSET_ACCOUNT_ID}
#export BSS_IMAGE_ASSET_REGION_SET="cn-north-1,cn-northwest-1"
#export BSS_FILE_ASSET_REGION_SET="cn-north-1,cn-northwest-1"
#run mkdir -p ${GLOBAL_S3_ASSETS_PATH}/${CN_ASSETS}
#export BSS_FILE_ASSET_PREFIX="${FILE_ASSET_PREFIX}${CN_ASSETS}"
#run npx cdk synth -c TargetPartition=aws-cn --json --output ${GLOBAL_S3_ASSETS_PATH}/${CN_ASSETS}
#sed -i "s|<TEMPLATE_BUILD_VERSION>|$BUILD_VERSION|"g ${GLOBAL_S3_ASSETS_PATH}/${CN_ASSETS}*template.json

export BSS_IMAGE_ASSET_ACCOUNT_ID=${AWS_ASSET_ACCOUNT_ID}
export BSS_FILE_ASSET_REGION_SET="$REGIONS"
export BSS_IMAGE_ASSET_REGION_SET=${BSS_FILE_ASSET_REGION_SET}

if [ ! -z "$AWS_ASSET_PUBLISH_ROLE" ]; then
run export BSS_FILE_ASSET_PUBLISHING_ROLE_ARN="$AWS_ASSET_PUBLISH_ROLE"
run export BSS_IMAGE_ASSET_PUBLISHING_ROLE_ARN="$AWS_ASSET_PUBLISH_ROLE"
fi

IFS=',' read -r -a prefixes <<< "$GLOBAL_ASSETS"
mkdir -p ${GLOBAL_S3_ASSETS_PATH}/${prefixes[0]}

export BSS_FILE_ASSET_PREFIX="${FILE_ASSET_PREFIX}${prefixes[0]}"
run npx cdk synth -c EnableDashboardCustomDomain=true --json --output ${GLOBAL_S3_ASSETS_PATH}/${prefixes[0]}
sed -i "s|<TEMPLATE_BUILD_VERSION>|$BUILD_VERSION|"g ${GLOBAL_S3_ASSETS_PATH}/${prefixes[0]}*template.json
mkdir -p ${GLOBAL_S3_ASSETS_PATH}/${prefixes[1]}
export BSS_FILE_ASSET_PREFIX="${FILE_ASSET_PREFIX}${prefixes[1]}"
run npx cdk synth --json --output ${GLOBAL_S3_ASSETS_PATH}/${prefixes[1]}
sed -i "s|<TEMPLATE_BUILD_VERSION>|$BUILD_VERSION|"g ${GLOBAL_S3_ASSETS_PATH}/${prefixes[1]}*template.json

run echo '763104351884.dkr.ecr.us-east-1.amazonaws.com'>>"${__dir}/ecr-repos"
run echo '727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn'>>"${__dir}/cn-ecr-repos"