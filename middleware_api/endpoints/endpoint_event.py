import json
import logging
import os
from datetime import datetime

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.util import record_latency_metrics
from libs.data_types import Endpoint
from libs.enums import EndpointStatus, EndpointType
from libs.utils import get_endpoint_by_name

tracer = Tracer()
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

autoscaling_client = boto3.client('application-autoscaling')
cw_client = boto3.client('cloudwatch')
sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)

cool_down_period = 15 * 60  # 15 minutes


# lambda: handle sagemaker events
@tracer.capture_lambda_handler
def handler(event, context):
    logger.info(json.dumps(event))
    endpoint_name = event['detail']['EndpointName']
    endpoint_status = event['detail']['EndpointStatus']

    try:
        endpoint = get_endpoint_by_name(endpoint_name)

        business_status = get_business_status(endpoint_status)

        update_endpoint_field(endpoint, 'endpoint_status', business_status)

        if business_status == EndpointStatus.IN_SERVICE.value:
            # start_time = datetime.strptime(endpoint['startTime']['S'], "%Y-%m-%d %H:%M:%S.%f")
            # deploy_seconds = int((datetime.now() - start_time).total_seconds())
            # update_endpoint_field(endpoint_deployment_job_id, 'deploy_seconds', deploy_seconds)
            current_time = str(datetime.now())
            update_endpoint_field(endpoint, 'endTime', current_time)

            record_latency_metrics(start_time=endpoint.startTime, metric_name='InService', service='Endpoint')

            # if it is the first time in service
            if not endpoint.endTime:
                check_and_enable_autoscaling(endpoint, 'prod')

        # update the instance count if the endpoint is not deleting or deleted
        if business_status not in [EndpointStatus.DELETING.value, EndpointStatus.DELETED.value]:
            status = sagemaker.describe_endpoint(EndpointName=endpoint_name)
            logger.info(f"Endpoint status: {status}")
            if 'ProductionVariants' in status:
                instance_count = status['ProductionVariants'][0]['CurrentInstanceCount']
                update_endpoint_field(endpoint, 'current_instance_count', instance_count)
        else:
            delete_ep_model_config(endpoint_name)
            ddb_service.delete_item(sagemaker_endpoint_table,
                                    keys={'EndpointDeploymentJobId': endpoint.EndpointDeploymentJobId})

        if business_status == EndpointStatus.FAILED.value:
            update_endpoint_field(endpoint, 'error', event['FailureReason'])

    except Exception as e:
        delete_ep_model_config(endpoint_name)
        logger.error(e, exc_info=True)

    return {'statusCode': 200}


def delete_ep_model_config(endpoint_name: str):
    try:
        sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_name)
    except Exception as e:
        logger.error(e, exc_info=True)

    try:
        sagemaker.delete_model(ModelName=endpoint_name)
    except Exception as e:
        logger.error(e, exc_info=True)


def check_and_enable_autoscaling(ep: Endpoint, variant_name):
    if ep.autoscaling:
        enable_autoscaling(ep, variant_name)
    else:
        logger.info(f'no need to enable autoscaling')


@tracer.capture_method
def enable_autoscaling(ep: Endpoint, variant_name):
    tracer.put_annotation("variant_name", variant_name)
    max_instance_number = int(ep.max_instance_number)

    min_instance_number = 0
    if ep.endpoint_type == EndpointType.RealTime.value:
        min_instance_number = 1

    if ep.min_instance_number is not None:
        min_instance_number = int(ep.min_instance_number)

    # Register scalable target
    response = autoscaling_client.register_scalable_target(
        ServiceNamespace='sagemaker',
        ResourceId='endpoint/' + ep.endpoint_name + '/variant/' + variant_name,
        ScalableDimension='sagemaker:variant:DesiredInstanceCount',
        MinCapacity=min_instance_number,
        MaxCapacity=max_instance_number,
    )
    logger.info(f"Register scalable target response: {response}")

    if ep.endpoint_type == EndpointType.Async.value:
        enable_autoscaling_async(ep, variant_name)

    if ep.endpoint_type == EndpointType.RealTime.value:
        enable_autoscaling_real_time(ep, variant_name)


def enable_autoscaling_async(ep: Endpoint, variant_name):
    target_value = 3

    # Define scaling policy
    response = autoscaling_client.put_scaling_policy(
        PolicyName=f"{ep.endpoint_name}-Invocations-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the AWS service that provides the resource.
        ResourceId='endpoint/' + ep.endpoint_name + '/variant/' + variant_name,  # Endpoint name
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="TargetTrackingScaling",  # 'StepScaling'|'TargetTrackingScaling'
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": target_value,
            # The target value for the metric. - here the metric is - SageMakerVariantInvocationsPerInstance
            "CustomizedMetricSpecification": {
                "MetricName": "ApproximateBacklogSizePerInstance",
                "Namespace": "AWS/SageMaker",
                "Dimensions": [{"Name": "EndpointName", "Value": ep.endpoint_name}],
                "Statistic": "Average",
            },
            "ScaleInCooldown": 180,
            # The cooldown period helps you prevent your Auto Scaling group from launching or terminating
            "ScaleOutCooldown": 60
            # ScaleOutCooldown - The amount of time, in seconds, after a scale out activity completes before another
            # scale out activity can start.
        },
    )
    logger.info(f"Put scaling policy response")
    logger.info(json.dumps(response))
    alarms = response.get('Alarms')
    for alarm in alarms:
        alarm_name = alarm.get('AlarmName')
        logger.info(f"Alarm name: {alarm_name}")
        response = cw_client.describe_alarms(
            AlarmNames=[alarm_name]
        )
        logger.info(f"Describe alarm response")
        logger.info(response)
        comparison_operator = response.get('MetricAlarms')[0]['ComparisonOperator']
        if comparison_operator == "LessThanThreshold":
            period = cool_down_period  # 15 minutes
            evaluation_periods = 4
            datapoints_to_alarm = 4
            target_value = 1
        else:
            period = 30
            evaluation_periods = 1
            datapoints_to_alarm = 1
            target_value = 3
        response = cw_client.put_metric_alarm(
            AlarmName=alarm_name,
            Namespace='AWS/SageMaker',
            MetricName='ApproximateBacklogSizePerInstance',
            Statistic="Average",
            Period=period,
            EvaluationPeriods=evaluation_periods,
            DatapointsToAlarm=datapoints_to_alarm,
            Threshold=target_value,
            ComparisonOperator=comparison_operator,
            AlarmActions=response.get('MetricAlarms')[0]['AlarmActions'],
            Dimensions=[{'Name': 'EndpointName', 'Value': ep.endpoint_name}]
        )
        logger.info(f"Put metric alarm response")
        logger.info(response)

    step_policy_response = autoscaling_client.put_scaling_policy(
        PolicyName=f"{ep.endpoint_name}-HasBacklogWithoutCapacity-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the service that provides the resource.
        ResourceId='endpoint/' + ep.endpoint_name + '/variant/' + variant_name,
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
    logger.info(f"Put step scaling policy response: {step_policy_response}")

    cw_client.put_metric_alarm(
        AlarmName=f'{ep.endpoint_name}-HasBacklogWithoutCapacity-Alarm',
        MetricName='HasBacklogWithoutCapacity',
        Namespace='AWS/SageMaker',
        Statistic='Average',
        Period=30,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1,
        ComparisonOperator='GreaterThanOrEqualToThreshold',
        TreatMissingData='missing',
        Dimensions=[
            {'Name': 'EndpointName', 'Value': ep.endpoint_name},
        ],
        AlarmActions=[step_policy_response['PolicyARN']]
    )
    logger.info(f"Put metric alarm response: {step_policy_response}")

    logger.info(f"Autoscaling has been enabled for the endpoint: {ep.endpoint_name}")


@tracer.capture_method
def enable_autoscaling_real_time(ep: Endpoint, variant_name):
    tracer.put_annotation("variant_name", variant_name)
    target_value = 5

    # Define scaling policy
    response = autoscaling_client.put_scaling_policy(
        PolicyName=f"{ep.endpoint_name}-Invocations-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the AWS service that provides the resource.
        ResourceId='endpoint/' + ep.endpoint_name + '/variant/' + variant_name,  # Endpoint name
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="TargetTrackingScaling",  # 'StepScaling'|'TargetTrackingScaling'
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": target_value,
            "PredefinedMetricSpecification":
                {
                    "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
                },
            "ScaleInCooldown": 180,
            # The cooldown period helps you prevent your Auto Scaling group from launching or terminating
            "ScaleOutCooldown": 60
            # ScaleOutCooldown - The amount of time, in seconds, after a scale out activity completes before another
            # scale out activity can start.
        },
    )
    logger.info(f"Put scaling policy response")
    logger.info(json.dumps(response))
    alarms = response.get('Alarms')
    for alarm in alarms:
        alarm_name = alarm.get('AlarmName')
        logger.info(f"Alarm name: {alarm_name}")
        response = cw_client.describe_alarms(
            AlarmNames=[alarm_name]
        )
        logger.info(f"Describe alarm response")
        logger.info(response)
        comparison_operator = response.get('MetricAlarms')[0]['ComparisonOperator']
        if comparison_operator == "LessThanThreshold":
            period = cool_down_period  # 15 minutes
            evaluation_periods = 4
            datapoints_to_alarm = 4
            target_value = 1
        else:
            period = 30
            evaluation_periods = 1
            datapoints_to_alarm = 1
            target_value = 5
        response = cw_client.put_metric_alarm(
            AlarmName=alarm_name,
            Namespace='AWS/SageMaker',
            MetricName='InvocationsPerInstance',
            Statistic="Sum",
            Period=period,
            EvaluationPeriods=evaluation_periods,
            DatapointsToAlarm=datapoints_to_alarm,
            Threshold=target_value,
            ComparisonOperator=comparison_operator,
            AlarmActions=response.get('MetricAlarms')[0]['AlarmActions'],
            Dimensions=[
                {'Name': 'EndpointName', 'Value': ep.endpoint_name},
                {'Name': 'VariantName', 'Value': 'prod'},
            ]
        )
        logger.info(f"Put metric alarm response")
        logger.info(response)

    logger.info(f"Autoscaling has been enabled for the endpoint: {ep.endpoint_name}")


def update_endpoint_field(ep: Endpoint, field_name, field_value):
    logger.info(f"Updating DynamoDB {field_name} to {field_value} for: {ep.EndpointDeploymentJobId}")
    ddb_service.update_item(
        table=sagemaker_endpoint_table,
        key={'EndpointDeploymentJobId': ep.EndpointDeploymentJobId},
        field_name=field_name,
        value=field_value
    )


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
