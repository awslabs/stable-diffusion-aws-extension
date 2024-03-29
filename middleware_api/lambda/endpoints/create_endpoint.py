import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime

import boto3
from aws_lambda_powertools import Tracer

from common.const import PERMISSION_ENDPOINT_ALL, PERMISSION_ENDPOINT_CREATE
from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import bad_request, accepted
from libs.data_types import EndpointDeploymentJob
from libs.enums import EndpointStatus, EndpointType
from libs.utils import response_error, permissions_check

tracer = Tracer()
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')
aws_region = os.environ.get('AWS_REGION')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
ASYNC_SUCCESS_TOPIC = os.environ.get('SNS_INFERENCE_SUCCESS')
ASYNC_ERROR_TOPIC = os.environ.get('SNS_INFERENCE_ERROR')
INFERENCE_ECR_IMAGE_URL = os.environ.get("INFERENCE_ECR_IMAGE_URL")
QUEUE_URL = os.environ.get('COMFY_QUEUE_URL')
SYNC_TABLE = os.environ.get('COMFY_SYNC_TABLE')
INSTANCE_MONITOR_TABLE = os.environ.get('COMFY_INSTANCE_MONITOR_TABLE')
ESD_VERSION = os.environ.get("ESD_VERSION")

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class CreateEndpointEvent:
    instance_type: str
    autoscaling_enabled: bool
    assign_to_roles: [str]
    initial_instance_count: str
    max_instance_number: str = "1"
    min_instance_number: str = "0"
    endpoint_name: str = None
    # real-time / async
    endpoint_type: str = None
    custom_docker_image_uri: str = None
    custom_extensions: str = ""
    # service for: sd / comfy
    service_type: str = "sd"
    # todo will be removed
    creator: str = ""


def check_custom_extensions(event: CreateEndpointEvent):
    if event.custom_extensions:
        logger.info(f"custom_extensions: {event.custom_extensions}")
        extensions_array = re.split('[ ,\n]+', event.custom_extensions)
        extensions_array = list(set(extensions_array))
        extensions_array = list(filter(None, extensions_array))

        for extension in extensions_array:
            pattern = r'^https://github\.com/[^#/]+/[^#/]+\.git#[^#]+#[a-fA-F0-9]{40}$'
            if not re.match(pattern, extension):
                raise BadRequestException(
                    message=f"extension format is invalid: {extension}, valid format is like "
                            f"https://github.com/awslabs/stable-diffusion-aws-extension.git#main#"
                            f"a096556799b7b0686e19ec94c0dbf2ca74d8ffbc")

        # make extensions_array to string again
        event.custom_extensions = ','.join(extensions_array)

        logger.info(f"formatted custom_extensions: {event.custom_extensions}")

        if len(extensions_array) >= 3:
            raise BadRequestException(message="custom_extensions should be at most 3")

    return event


def get_docker_image_uri(event: CreateEndpointEvent):
    # if it has custom extensions, then start from file image
    if event.custom_docker_image_uri:
        return event.custom_docker_image_uri

    return INFERENCE_ECR_IMAGE_URL


# POST /endpoints
@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))
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

        event = check_custom_extensions(event)

        endpoint_id = str(uuid.uuid4())
        short_id = endpoint_id[:7]

        if event.endpoint_name:
            short_id = event.endpoint_name

        endpoint_type = event.endpoint_type.lower()
        model_name = f"esd-model-{endpoint_type}-{short_id}"
        endpoint_config_name = f"esd-config-{endpoint_type}-{short_id}"
        endpoint_name = f"esd-{endpoint_type}-{short_id}"

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

        _create_sagemaker_model(model_name, model_data_url, endpoint_name, endpoint_id, event)

        try:
            if event.endpoint_type == EndpointType.RealTime.value:
                _create_endpoint_config_provisioned(endpoint_config_name, model_name,
                                                    initial_instance_count, instance_type)
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
            custom_extensions=event.custom_extensions,
            service_type=event.service_type,
        ).__dict__

        ddb_service.put_items(table=sagemaker_endpoint_table, entries=data)
        logger.info(f"Successfully created endpoint deployment: {data}")

        return accepted(
            message=f"Endpoint deployment started: {endpoint_name}",
            data=data
        )
    except Exception as e:
        return response_error(e)


@tracer.capture_method
def _create_sagemaker_model(name, model_data_url, endpoint_name, endpoint_id, event: CreateEndpointEvent):
    tracer.put_annotation('endpoint_name', endpoint_name)
    image_url = get_docker_image_uri(event)

    primary_container = {
        'Image': image_url,
        'ModelDataUrl': model_data_url,
        'Environment': {
            'LOG_LEVEL': os.environ.get('LOG_LEVEL') or logging.ERROR,
            'S3_BUCKET_NAME': S3_BUCKET_NAME,
            'IMAGE_URL': image_url,
            'INSTANCE_TYPE': event.instance_type,
            'ENDPOINT_NAME': endpoint_name,
            'ENDPOINT_ID': endpoint_id,
            'EXTENSIONS': event.custom_extensions,
            'CREATED_AT': datetime.utcnow().isoformat(),
            'COMFY_QUEUE_URL': QUEUE_URL or '',
            'COMFY_SYNC_TABLE': SYNC_TABLE or '',
            'COMFY_INSTANCE_MONITOR_TABLE': INSTANCE_MONITOR_TABLE or '',
            'ESD_VERSION': ESD_VERSION,
            'SERVICE_TYPE': event.service_type,
            'ON_DOCKER': 'true',
        },
    }

    tracer.put_metadata('primary_container', primary_container)

    logger.info(f"Creating model resource PrimaryContainer: {primary_container}")

    response = sagemaker.create_model(
        ModelName=name,
        PrimaryContainer=primary_container,
        ExecutionRoleArn=os.environ.get("EXECUTION_ROLE_ARN"),
    )
    logger.info(f"Successfully created model resource: {response}")


def get_production_variants(model_name, instance_type, initial_instance_count):
    return [
        {
            'VariantName': 'prod',
            'ModelName': model_name,
            'InitialInstanceCount': initial_instance_count,
            'InstanceType': instance_type,
            "ModelDataDownloadTimeoutInSeconds": 60 * 30,  # Specify the model download timeout in seconds.
            "ContainerStartupHealthCheckTimeoutInSeconds": 60 * 10,  # Specify the health checkup timeout in seconds
        }
    ]


@tracer.capture_method
def _create_endpoint_config_provisioned(endpoint_config_name, model_name, initial_instance_count,
                                        instance_type):
    production_variants = get_production_variants(model_name, instance_type, initial_instance_count)

    logger.info(f"Creating endpoint configuration ProductionVariants: {production_variants}")

    response = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=production_variants
    )
    logger.info(f"Successfully created endpoint configuration: {response}")


@tracer.capture_method
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

    production_variants = get_production_variants(model_name, instance_type, initial_instance_count)

    logger.info(f"Creating endpoint configuration AsyncInferenceConfig: {async_inference_config}")
    logger.info(f"Creating endpoint configuration ProductionVariants: {production_variants}")

    response = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        AsyncInferenceConfig=async_inference_config,
        ProductionVariants=production_variants
    )
    logger.info(f"Successfully created endpoint configuration: {response}")
