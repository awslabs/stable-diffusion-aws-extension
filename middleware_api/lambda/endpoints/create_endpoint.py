import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime

import boto3

from common.const import PERMISSION_ENDPOINT_ALL, PERMISSION_ENDPOINT_CREATE
from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import bad_request, accepted
from libs.data_types import EndpointDeploymentJob
from libs.enums import EndpointStatus, EndpointType
from libs.utils import response_error, permissions_check

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')
aws_region = os.environ.get('AWS_REGION')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
ASYNC_SUCCESS_TOPIC = os.environ.get('SNS_INFERENCE_SUCCESS')
ASYNC_ERROR_TOPIC = os.environ.get('SNS_INFERENCE_ERROR')
INFERENCE_ECR_IMAGE_URL = os.environ.get("INFERENCE_ECR_IMAGE_URL")

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class CreateEndpointEvent:
    instance_type: str
    autoscaling_enabled: bool
    assign_to_roles: [str]
    creator: str
    initial_instance_count: str
    max_instance_number: str = "1"
    min_instance_number: str = "0"
    endpoint_name: str = None
    # real-time / serverless / async
    endpoint_type: str = None
    custom_docker_image_uri: str = None


def get_docker_image_uri(event: CreateEndpointEvent):
    image_url = INFERENCE_ECR_IMAGE_URL

    if event.custom_docker_image_uri:
        image_url = event.custom_docker_image_uri

        if aws_region.startswith('cn-'):
            pattern = rf'^([a-zA-Z0-9][a-zA-Z0-9.-]*\.dkr\.ecr\.{aws_region}\.amazonaws\.com\.cn)/([^/]+)/([^:]+):(.+)$'
        else:
            pattern = rf'^([a-zA-Z0-9][a-zA-Z0-9.-]*\.dkr\.ecr\.{aws_region}\.amazonaws\.com)/([^/]+)/([^:]+):(.+)$'

        if not re.match(pattern, image_url):
            raise Exception(f"Invalid docker image uri {image_url}")

    return image_url


# POST /endpoints
def handler(raw_event, ctx):
    logger.info(f"Received event: {raw_event}")
    logger.info(f"Received ctx: {ctx}")

    try:
        event = CreateEndpointEvent(**json.loads(raw_event['body']))

        permissions_check(raw_event, [PERMISSION_ENDPOINT_ALL, PERMISSION_ENDPOINT_CREATE])

        if event.endpoint_type not in EndpointType.List.value:
            raise BadRequestException(message=f"{event.endpoint_type} endpoint is not supported yet")

        if int(event.initial_instance_count) < 1:
            raise BadRequestException(f"initial_instance_count should be at least 1: {event.endpoint_name}")

        if event.autoscaling_enabled:
            if event.endpoint_type == EndpointType.RealTime.value and int(event.min_instance_number) < 1:
                raise BadRequestException(
                    f"min_instance_number should be at least 1 for real-time endpoint: {event.endpoint_name}")

            if event.endpoint_type == EndpointType.Async.value and int(event.min_instance_number) < 0:
                raise BadRequestException(
                    f"min_instance_number should be at least 0 for async endpoint: {event.endpoint_name}")

        endpoint_id = str(uuid.uuid4())
        short_id = endpoint_id[:7]

        if event.endpoint_name:
            short_id = event.endpoint_name

        endpoint_type = event.endpoint_type.lower()
        model_name = f"esd-model-{endpoint_type}-{short_id}"
        endpoint_config_name = f"esd-config-{endpoint_type}-{short_id}"
        endpoint_name = f"esd-{endpoint_type}-{short_id}"

        image_url = get_docker_image_uri(event)

        model_data_url = f"s3://{S3_BUCKET_NAME}/data/model.tar.gz"

        s3_output_path = f"s3://{S3_BUCKET_NAME}/sagemaker_output/"

        initial_instance_count = int(event.initial_instance_count) if event.initial_instance_count else 1
        instance_type = event.instance_type

        endpoint_rows = ddb_service.scan(sagemaker_endpoint_table, filters=None)
        for endpoint_row in endpoint_rows:
            endpoint = EndpointDeploymentJob(**(ddb_service.deserialize(endpoint_row)))
            # Compatible with fields used in older data, endpoint.status must be 'deleted'
            if endpoint.endpoint_status != EndpointStatus.DELETED.value and endpoint.status != 'deleted':
                for role in event.assign_to_roles:
                    if role in endpoint.owner_group_or_role:
                        return bad_request(
                            message=f"role [{role}] has a valid endpoint already, not allow to have another one")

        _create_sagemaker_model(model_name, image_url, model_data_url, instance_type, endpoint_name, endpoint_id)

        try:
            if event.endpoint_type == EndpointType.RealTime.value:
                _create_endpoint_config_provisioned(endpoint_config_name, model_name,
                                                    initial_instance_count, instance_type)
            elif event.endpoint_type == EndpointType.Serverless.value:
                _create_endpoint_config_serverless(endpoint_config_name)
            elif event.endpoint_type == EndpointType.Async.value:
                _create_endpoint_config_async(endpoint_config_name, s3_output_path, model_name,
                                              initial_instance_count, instance_type)
        except Exception as e:
            logger.error(f"error creating endpoint config with exception: {e}")
            sagemaker.delete_model(ModelName=model_name)
            return bad_request(message=str(e))

        try:
            response = sagemaker.create_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=endpoint_config_name
            )
            logger.info(f"Successfully created endpoint: {response}")
        except Exception as e:
            logger.error(f"error creating endpoint with exception: {e}")
            sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
            sagemaker.delete_model(ModelName=model_name)
            return bad_request(message=str(e))

        data = EndpointDeploymentJob(
            EndpointDeploymentJobId=endpoint_id,
            endpoint_name=endpoint_name,
            startTime=str(datetime.now()),
            endpoint_status=EndpointStatus.CREATING.value,
            autoscaling=event.autoscaling_enabled,
            owner_group_or_role=event.assign_to_roles,
            current_instance_count="0",
            instance_type=instance_type,
            endpoint_type=event.endpoint_type,
            min_instance_number=event.min_instance_number,
            max_instance_number=event.max_instance_number,
        ).__dict__

        ddb_service.put_items(table=sagemaker_endpoint_table, entries=data)
        logger.info(f"Successfully created endpoint deployment: {data}")

        return accepted(
            message=f"Endpoint deployment started: {endpoint_name}",
            data=data
        )
    except Exception as e:
        return response_error(e)


def _create_sagemaker_model(name, image_url, model_data_url, instance_type, endpoint_name, endpoint_id):
    primary_container = {
        'Image': image_url,
        'ModelDataUrl': model_data_url,
        'Environment': {
            'EndpointID': 'OUR_ID',
            'LOG_LEVEL': os.environ.get('LOG_LEVEL') or logging.ERROR,
            'BUCKET_NAME': S3_BUCKET_NAME,
            'INSTANCE_TYPE': instance_type,
            'ENDPOINT_NAME': endpoint_name,
            'ENDPOINT_ID': endpoint_id,
            'CREATED_AT': datetime.utcnow().isoformat(),
        },
    }

    logger.info(f"Creating model resource PrimaryContainer: {primary_container}")

    response = sagemaker.create_model(
        ModelName=name,
        PrimaryContainer=primary_container,
        ExecutionRoleArn=os.environ.get("EXECUTION_ROLE_ARN"),
    )
    logger.info(f"Successfully created model resource: {response}")


def _create_endpoint_config_provisioned(endpoint_config_name, model_name, initial_instance_count,
                                        instance_type):
    production_variants = [
        {
            'VariantName': 'prod',
            'ModelName': model_name,
            'InitialInstanceCount': initial_instance_count,
            'InstanceType': instance_type,
            "ModelDataDownloadTimeoutInSeconds": 1800,  # Specify the model download timeout in seconds.
            "ContainerStartupHealthCheckTimeoutInSeconds": 1800,  # Specify the health checkup timeout in seconds
        }
    ]

    logger.info(f"Creating endpoint configuration ProductionVariants: {production_variants}")

    response = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=production_variants
    )
    logger.info(f"Successfully created endpoint configuration: {response}")


def _create_endpoint_config_serverless(endpoint_config_name):
    production_variants = [
        {
            'MemorySizeInMB': 2048,
            'MaxConcurrency': 100
        }
    ]

    logger.info(f"Creating endpoint configuration ProductionVariants: {production_variants}")

    response = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=production_variants
    )
    logger.info(f"Successfully created endpoint configuration: {response}")


def _create_endpoint_config_async(endpoint_config_name, s3_output_path, model_name, initial_instance_count,
                                  instance_type):
    async_inference_config = {
        "OutputConfig": {
            "S3OutputPath": s3_output_path,
            "NotificationConfig": {
                "SuccessTopic": ASYNC_SUCCESS_TOPIC,
                "ErrorTopic": ASYNC_ERROR_TOPIC
            }
        },
        "ClientConfig": {
            # (Optional) Specify the max number of inflight invocations per instance
            # If no value is provided, Amazon SageMaker will choose an optimal value for you
            "MaxConcurrentInvocationsPerInstance": 1
        }
    }

    production_variants = [
        {
            'VariantName': 'prod',
            'ModelName': model_name,
            'InitialInstanceCount': initial_instance_count,
            'InstanceType': instance_type,
            "ModelDataDownloadTimeoutInSeconds": 1800,  # Specify the model download timeout in seconds.
            "ContainerStartupHealthCheckTimeoutInSeconds": 1800,  # Specify the health checkup timeout in seconds
        }
    ]

    logger.info(f"Creating endpoint configuration AsyncInferenceConfig: {async_inference_config}")
    logger.info(f"Creating endpoint configuration ProductionVariants: {production_variants}")

    response = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        AsyncInferenceConfig=async_inference_config,
        ProductionVariants=production_variants
    )
    logger.info(f"Successfully created endpoint configuration: {response}")
