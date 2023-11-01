import os
import uuid
import boto3
from datetime import datetime
from aws_lambda_powertools import Logger
from botocore.exceptions import BotoCoreError, ClientError
from common.ddb_service.client import DynamoDbUtilsService
from multi_users.utils import get_user_roles, check_user_permissions
from _types import EndpointDeploymentJob
from _enums import EndpointStatus

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
ASYNC_SUCCESS_TOPIC = os.environ.get('SNS_INFERENCE_SUCCESS')
ASYNC_ERROR_TOPIC = os.environ.get('SNS_INFERENCE_ERROR')
INFERENCE_ECR_IMAGE_URL = os.environ.get("INFERENCE_ECR_IMAGE_URL")

logger = Logger(service="sagemaker_endpoint_api", level="INFO")
sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)


# GET /endpoints?name=SageMaker_Endpoint_Name&username=&filter=key:value,key:value
def list_all_sagemaker_endpoints(event, ctx):
    _filter = {}
    if 'queryStringParameters' not in event:
        return {
            'statusCode': '500',
            'error': 'query parameter status and types are needed'
        }

    parameters = event['queryStringParameters']

    endpoint_deployment_job_id = parameters['endpointDeploymentJobId'] if 'endpointDeploymentJobId' in parameters and \
                                                                          parameters[
                                                                              'endpointDeploymentJobId'] else None
    username = parameters['username'] if 'username' in parameters and parameters['username'] else None

    if endpoint_deployment_job_id:
        scan_rows = ddb_service.query_items(sagemaker_endpoint_table,
                                            key_values={'EndpointDeploymentJobId': endpoint_deployment_job_id},
                                            )
    else:
        scan_rows = ddb_service.scan(sagemaker_endpoint_table, filters=None)

    results = []
    user_roles = []
    if username:
        user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

    if 'x-auth' in event and not event['x-auth']['role']:
        event['x-auth']['role'] = user_roles

    for row in scan_rows:

        # Compatible with fields used in older data, must be 'deleted'
        if 'status' in row and row['status']['S'] == 'deleted':
            row['endpoint_status']['S'] = EndpointStatus.DELETED.value

        endpoint = EndpointDeploymentJob(**(ddb_service.deserialize(row)))
        if username and check_user_permissions(endpoint.owner_group_or_role, user_roles, username):
            results.append(endpoint.__dict__)
        elif 'x-auth' in event and 'IT Operator' in event['x-auth']['role']:
            # todo: this is not save to do without checking current user roles
            results.append(endpoint.__dict__)

    return {
        'statusCode': 200,
        'endpoints': results
    }


# DELETE /endpoints
def delete_sagemaker_endpoints(event, ctx):
    try:
        # delete sagemaker endpoints in the same loop
        for endpoint in event['delete_endpoint_list']:

            try:
                delete_response = sagemaker.delete_endpoint(EndpointName=endpoint)
                logger.info(delete_response)

            except (BotoCoreError, ClientError) as error:
                if error.response['Error']['Code'] == 'ResourceNotFound':
                    logger.info("Endpoint not found, no need to delete.")
                else:
                    logger.error(error)

        return "Endpoint deleted"
    except Exception as e:
        logger.error(f"error deleting sagemaker endpoint with exception: {e}")
        return f"error deleting sagemaker endpoint with exception: {e}"


# POST /endpoints
def sagemaker_endpoint_create_api(event, ctx):
    logger.info(f"Received event: {event}")
    logger.info(f"Received ctx: {ctx}")

    try:
        endpoint_deployment_id = str(uuid.uuid4())
        shortId = endpoint_deployment_id[:7]
        endpoint_name_from_request = event["endpoint_name"]
        sagemaker_model_name = f"infer-model-{shortId}"
        sagemaker_endpoint_config = f"infer-config-{shortId}"

        if not endpoint_name_from_request.strip():
            sagemaker_endpoint_name = f"infer-endpoint-{shortId}"
        else:
            sagemaker_endpoint_name = endpoint_name_from_request

        image_url = INFERENCE_ECR_IMAGE_URL

        model_data_url = f"s3://{S3_BUCKET_NAME}/data/model.tar.gz"

        s3_output_path = f"s3://{S3_BUCKET_NAME}/sagemaker_output/"

        initial_instance_count = int(event.get("initial_instance_count", 1))
        instance_type = event["instance_type"]

        create_model(sagemaker_model_name, image_url, model_data_url)

        create_endpoint_config(sagemaker_endpoint_config, s3_output_path, sagemaker_model_name, initial_instance_count,
                               instance_type)

        logger.info('Creating new model endpoint...')
        response = sagemaker.create_endpoint(
            EndpointName=sagemaker_endpoint_name,
            EndpointConfigName=sagemaker_endpoint_config
        )
        logger.info(f"Successfully created endpoint: {response}")

        current_time = str(datetime.now())
        raw = {
            'EndpointDeploymentJobId': endpoint_deployment_id,
            'endpoint_name': sagemaker_endpoint_name,
            'startTime': current_time,
            'endpoint_status': EndpointStatus.CREATING.value,
            'max_instance_number': event['initial_instance_count'],
            'autoscaling': event['autoscaling_enabled'],
            'owner_group_or_role': event['assign_to_roles'],
            'current_instance_count': "0",
        }
        ddb_service.put_items(table=sagemaker_endpoint_table, entries=raw)
        logger.info(f"Successfully created endpoint deployment: {raw}")

        return {
            'statusCode': 200,
            'message': "Endpoint deployment started",
            'data': raw
        }
    except Exception as e:
        logger.error(e)
        return {
            'statusCode': 200,
            'message': str(e),
        }


def create_model(name, image_url, model_data_url):
    PrimaryContainer = {
        'Image': image_url,
        'ModelDataUrl': model_data_url,
        'Environment': {
            'EndpointID': 'OUR_ID'
        },
    }

    logger.info(f"Creating model resource PrimaryContainer: {PrimaryContainer}")

    response = sagemaker.create_model(
        ModelName=name,
        PrimaryContainer=PrimaryContainer,
        ExecutionRoleArn=os.environ.get("EXECUTION_ROLE_ARN"),
    )
    logger.info(f"Successfully created model resource: {response}")


def create_endpoint_config(endpoint_config_name, s3_output_path, model_name, initial_instance_count, instance_type):
    AsyncInferenceConfig = {
        "OutputConfig": {
            "S3OutputPath": s3_output_path,
            "NotificationConfig": {
                "SuccessTopic": ASYNC_SUCCESS_TOPIC,
                "ErrorTopic": ASYNC_ERROR_TOPIC
            }
        }
    }

    ProductionVariants = [
        {
            'VariantName': 'prod',
            'ModelName': model_name,
            'InitialInstanceCount': initial_instance_count,
            'InstanceType': instance_type
        }
    ]

    logger.info(f"Creating endpoint configuration AsyncInferenceConfig: {AsyncInferenceConfig}")
    logger.info(f"Creating endpoint configuration ProductionVariants: {ProductionVariants}")

    response = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        AsyncInferenceConfig=AsyncInferenceConfig,
        ProductionVariants=ProductionVariants
    )
    logger.info(f"Successfully created endpoint configuration: {response}")


def sagemaker_endpoint_events(event, context):
    logger.info(event)
    endpoint_name = event['detail']['EndpointName']
    endpoint_status = event['detail']['EndpointStatus']

    item = get_endpoint_with_endpoint_name(endpoint_name)
    if item:

        endpoint_deployment_job_id = item['EndpointDeploymentJobId']

        business_status = get_business_status(endpoint_status)

        update_endpoint_field(endpoint_deployment_job_id, 'endpoint_status', business_status)

        if business_status in [EndpointStatus.DELETING.value, EndpointStatus.DELETED.value]:
            status = sagemaker.describe_endpoint(EndpointName=endpoint_name)
            logger.info(f"Endpoint status: {status}")
            if 'ProductionVariants' in status:
                instance_count = status['ProductionVariants'][0]['CurrentInstanceCount']
                update_endpoint_field(endpoint_deployment_job_id, 'current_instance_count', instance_count)

        if business_status == EndpointStatus.DELETED.value:
            update_endpoint_field(endpoint_deployment_job_id, 'current_instance_count', 0)
            endpoint_config_name = event['detail']['EndpointConfigName']
            model_name = event['detail']['ModelName']
            # todo need test
            try:
                sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
                sagemaker.delete_model(ModelName=model_name)
            except Exception as e:
                logger.error(f"error deleting endpoint config and model with exception: {e}")

        if business_status == EndpointStatus.IN_SERVICE.value:
            current_time = str(datetime.now())
            update_endpoint_field(endpoint_deployment_job_id, 'endTime', current_time)
            check_and_enable_autoscaling(item, 'prod')
        elif business_status == EndpointStatus.FAILED.value:
            update_endpoint_field(endpoint_deployment_job_id, 'error', event['FailureReason'])

    else:
        logger.error(f"No matching DynamoDB record found for endpoint: {endpoint_name}")

    return {'statusCode': 200}


def check_and_enable_autoscaling(item, variant_name):
    autoscaling = item['autoscaling']['BOOL']
    endpoint_name = item['endpoint_name']['S']
    max_instance_number = item['max_instance_number']['S']

    logger.info(f"autoscaling: {autoscaling}")
    logger.info(f"endpoint_name: {endpoint_name}")
    logger.info(f"max_instance_number: {max_instance_number}")

    if str(autoscaling) == 'True':
        if max_instance_number.isdigit():
            enable_autoscaling(endpoint_name, variant_name, 0, int(max_instance_number))
        else:
            logger.info(f"the max_number field is not digit, just fallback to 1")
            enable_autoscaling(endpoint_name, variant_name, 0, 1)
    else:
        logger.info(f'autoscaling_enabled is {autoscaling}, no need to enable autoscaling')


def enable_autoscaling(endpoint_name, variant_name, low_value, high_value):
    client = boto3.client('application-autoscaling')

    # Register scalable target
    response = client.register_scalable_target(
        ServiceNamespace='sagemaker',
        ResourceId='endpoint/' + endpoint_name + '/variant/' + variant_name,
        ScalableDimension='sagemaker:variant:DesiredInstanceCount',
        MinCapacity=low_value,
        MaxCapacity=high_value,
    )

    # Define scaling policy

    response = client.put_scaling_policy(
        PolicyName="Invocations-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the AWS service that provides the resource.
        ResourceId='endpoint/' + endpoint_name + '/variant/' + variant_name,  # Endpoint name
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="TargetTrackingScaling",  # 'StepScaling'|'TargetTrackingScaling'
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": 5.0,
            # The target value for the metric. - here the metric is - SageMakerVariantInvocationsPerInstance
            "CustomizedMetricSpecification": {
                "MetricName": "ApproximateBacklogSizePerInstance",
                "Namespace": "AWS/SageMaker",
                "Dimensions": [{"Name": "EndpointName", "Value": endpoint_name}],
                "Statistic": "Average",
            },
            "ScaleInCooldown": 180,
            # The cooldown period helps you prevent your Auto Scaling group from launching or terminating
            "ScaleOutCooldown": 60
            # ScaleOutCooldown - The amount of time, in seconds, after a scale out activity completes before another
            # scale out activity can start.
        },
    )

    step_policy_response = client.put_scaling_policy(
        PolicyName="HasBacklogWithoutCapacity-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the service that provides the resource.
        ResourceId='endpoint/' + endpoint_name + '/variant/' + variant_name,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="StepScaling",  # 'StepScaling' or 'TargetTrackingScaling'
        StepScalingPolicyConfiguration={
            "AdjustmentType": "ChangeInCapacity",
            # Specifies whether the ScalingAdjustment value in the StepAdjustment property is an absolute number or a
            # percentage of the current capacity.
            "MetricAggregationType": "Average",  # The aggregation type for the CloudWatch metrics.
            "Cooldown": 180,  # The amount of time, in seconds, to wait for a previous scaling activity to take effect.
            "StepAdjustments":  # A set of adjustments that enable you to scale based on the size of the alarm breach.
                [
                    {
                        "MetricIntervalLowerBound": 0,
                        "ScalingAdjustment": 1
                    }
                ]
        },
    )

    cw_client = boto3.client('cloudwatch')

    cw_client.put_metric_alarm(
        AlarmName='stable-diffusion-hasbacklogwithoutcapacity-alarm',
        MetricName='HasBacklogWithoutCapacity',
        Namespace='AWS/SageMaker',
        Statistic='Average',
        EvaluationPeriods=2,
        DatapointsToAlarm=2,
        Threshold=1,
        ComparisonOperator='GreaterThanOrEqualToThreshold',
        TreatMissingData='missing',
        Dimensions=[
            {'Name': 'EndpointName', 'Value': endpoint_name},
        ],
        Period=60,
        AlarmActions=[step_policy_response['PolicyARN']]
    )

    print(f"Autoscaling has been enabled for the endpoint: {endpoint_name}")


def update_endpoint_field(endpoint_deployment_job_id, field_name, field_value):
    logger.info(f"Updating DynamoDB {field_name} to {field_value} for: {endpoint_deployment_job_id}")
    ddb_service.update_item(
        table=sagemaker_endpoint_table,
        key={'EndpointDeploymentJobId': endpoint_deployment_job_id['S']},
        field_name=field_name,
        value=field_value
    )


def get_endpoint_with_endpoint_name(endpoint_name):
    try:
        record_list = ddb_service.scan(table=sagemaker_endpoint_table, filters={
            'endpoint_name': endpoint_name,
        })

        if len(record_list) == 0:
            logger.error("There is no endpoint deployment job info item with endpoint name:" + endpoint_name)
            return {}

        logger.info(record_list[0])
        return record_list[0]
    except Exception as e:
        logger.error(e)
        return {}


def get_business_status(status):
    """
    Convert SageMaker endpoint status to business status
    :param status: EventBridge event status(upper case)
    :return: business status
    """
    switcher = {
        "IN_SERVICE": EndpointStatus.IN_SERVICE.value,
        "CREATING": EndpointStatus.CREATING.value,
        "DELETED": EndpointStatus.DELETED.value,
        "FAILED": EndpointStatus.FAILED.value,
        "UPDATING": EndpointStatus.UPDATING.value,
        "DELETING": EndpointStatus.DELETING.value,
    }
    return switcher.get(status, status)
