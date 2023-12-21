import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime

import boto3

from common.ddb_service.client import DynamoDbUtilsService
from common.enums import EndpointStatus
from common.response import ok, bad_request
from common.types import EndpointDeploymentJob
from common.utils import get_permissions_by_username

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
ASYNC_SUCCESS_TOPIC = os.environ.get('SNS_INFERENCE_SUCCESS')
ASYNC_ERROR_TOPIC = os.environ.get('SNS_INFERENCE_ERROR')
INFERENCE_ECR_IMAGE_URL = os.environ.get("INFERENCE_ECR_IMAGE_URL")

# logger = Logger(service="sagemaker_endpoint_api", level="INFO")
logger = logging.getLogger('inference_v2')
logger.setLevel(logging.INFO)
sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class CreateEndpointEvent:
    instance_type: str
    initial_instance_count: str
    autoscaling_enabled: bool
    assign_to_roles: [str]
    creator: str
    endpoint_name: str = None


# POST /endpoints
def handler(raw_event, ctx):
    logger.info(f"Received event: {raw_event}")
    logger.info(f"Received ctx: {ctx}")
    event = CreateEndpointEvent(**json.loads(raw_event['body']))

    endpoint_deployment_id = str(uuid.uuid4())
    short_id = endpoint_deployment_id[:7]

    if event.endpoint_name:
        short_id = event.endpoint_name

    model_name = f"infer-model-{short_id}"
    endpoint_config_name = f"infer-config-{short_id}"
    endpoint_name = f"infer-endpoint-{short_id}"

    try:
        image_url = INFERENCE_ECR_IMAGE_URL

        model_data_url = f"s3://{S3_BUCKET_NAME}/data/model.tar.gz"

        s3_output_path = f"s3://{S3_BUCKET_NAME}/sagemaker_output/"

        initial_instance_count = int(event.initial_instance_count) if event.initial_instance_count else 1
        instance_type = event.instance_type

        # check if roles have already linked to an endpoint?
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)
        if 'sagemaker_endpoint' not in creator_permissions or \
                ('all' not in creator_permissions['sagemaker_endpoint'] and 'create' not in creator_permissions[
                    'sagemaker_endpoint']):
            return bad_request(message=f"Creator {event.creator} has no permission to create Sagemaker")

        endpoint_rows = ddb_service.scan(sagemaker_endpoint_table, filters=None)
        for endpoint_row in endpoint_rows:
            endpoint = EndpointDeploymentJob(**(ddb_service.deserialize(endpoint_row)))
            # Compatible with fields used in older data, endpoint.status must be 'deleted'
            if endpoint.endpoint_status != EndpointStatus.DELETED.value and endpoint.status != 'deleted':
                for role in event.assign_to_roles:
                    if role in endpoint.owner_group_or_role:
                        return bad_request(
                            message=f"role [{role}] has a valid endpoint already, not allow to have another one")

        _create_sagemaker_model(model_name, image_url, model_data_url)

        try:
            _create_sagemaker_endpoint_config(endpoint_config_name, s3_output_path, model_name,
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
            EndpointDeploymentJobId=endpoint_deployment_id,
            endpoint_name=endpoint_name,
            startTime=str(datetime.now()),
            endpoint_status=EndpointStatus.CREATING.value,
            max_instance_number=event.initial_instance_count,
            autoscaling=event.autoscaling_enabled,
            owner_group_or_role=event.assign_to_roles,
            current_instance_count="0",
        ).__dict__

        ddb_service.put_items(table=sagemaker_endpoint_table, entries=data)
        logger.info(f"Successfully created endpoint deployment: {data}")

        return ok(
            message=f"Endpoint deployment started: {endpoint_name}",
            data=data
        )
    except Exception as e:
        logger.error(e)
        return bad_request(message=str(e))


def _create_sagemaker_model(name, image_url, model_data_url):
    primary_container = {
        'Image': image_url,
        'ModelDataUrl': model_data_url,
        'Environment': {
            'EndpointID': 'OUR_ID'
        },
    }

    logger.info(f"Creating model resource PrimaryContainer: {primary_container}")

    response = sagemaker.create_model(
        ModelName=name,
        PrimaryContainer=primary_container,
        ExecutionRoleArn=os.environ.get("EXECUTION_ROLE_ARN"),
    )
    logger.info(f"Successfully created model resource: {response}")


def _create_sagemaker_endpoint_config(endpoint_config_name, s3_output_path, model_name, initial_instance_count,
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
            'InstanceType': instance_type
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
