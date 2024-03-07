import json
import logging
import os
from datetime import datetime

from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.const import PERMISSION_INFERENCE_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import accepted, bad_request
from get_inference_job import get_infer_data
from inference_libs import parse_result, update_inference_job_table
from libs.data_types import InferenceJob, InvocationsRequest
from libs.enums import EndpointType
from libs.utils import response_error, permissions_check, log_execution_time

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

inference_table_name = os.environ.get('INFERENCE_JOB_TABLE')

ddb_service = DynamoDbUtilsService(logger=logger)

predictors = {}


def handler(event, _):
    logger.info(json.dumps(event))
    _filter = {}

    try:
        inference_id = event['pathParameters']['id']

        if not inference_id:
            raise BadRequestException("InferenceJobId is required")

        username = permissions_check(event, [PERMISSION_INFERENCE_ALL])

        # get the inference job from ddb by job id
        inference_raw = ddb_service.get_item(inference_table_name, {
            'InferenceJobId': inference_id
        })

        if inference_raw is None or len(inference_raw) == 0:
            raise BadRequestException(f"InferenceJobId {inference_id} not found")

        job = InferenceJob(**inference_raw)

        return start_inference_job(job, username)

    except Exception as e:
        return response_error(e)


def start_inference_job(job: InferenceJob, username):
    endpoint_name = job.params['sagemaker_inference_endpoint_name']
    models = {}
    if 'used_models' in job.params:
        models = {
            "space_free_size": 4e10,
            **job.params['used_models'],
        }

    payload = InvocationsRequest(
        task=job.taskType,
        username=username,
        models=models,
        param_s3=job.params['input_body_s3'],
        endpoint_payload=job.endpoint_payload
    )

    logger.info(f"payload: {payload}")

    update_inference_job_table(job.InferenceJobId, 'startTime', str(datetime.now()))

    if job.inference_type == EndpointType.RealTime.value:
        return real_time_inference(payload, job, endpoint_name)

    return async_inference(payload, job, endpoint_name)


def real_time_inference(payload, job: InferenceJob, endpoint_name):
    try:

        sagemaker_out = predictor_predict(endpoint_name=endpoint_name,
                                          data=payload.__dict__,
                                          inference_id=job.InferenceJobId,
                                          )

        if 'error' in sagemaker_out:
            update_inference_job_table(job.InferenceJobId, 'sagemakerRaw', str(sagemaker_out))
            raise Exception(str(sagemaker_out))

        parse_result(sagemaker_out, job.InferenceJobId, job.taskType, endpoint_name)

        return get_infer_data(job.InferenceJobId)
    except Exception as e:
        print(e)
        return bad_request(message=str(e))


@log_execution_time
def get_predict_client(endpoint_name):
    if endpoint_name in predictors:
        return predictors[endpoint_name]

    predictor = Predictor(endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    predictors[endpoint_name] = predictor

    return predictor


@log_execution_time
def get_predict_async_client(endpoint_name):
    if endpoint_name in predictors:
        return predictors[endpoint_name]

    predictor = Predictor(endpoint_name)
    predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    predictors[endpoint_name] = predictor

    return predictor


@log_execution_time
def predictor_predict(endpoint_name, data, inference_id):
    return get_predict_client(endpoint_name).predict(data=data, inference_id=inference_id)


@log_execution_time
def predictor_predict_async(endpoint_name, data, inference_id):
    initial_args = {"InvocationTimeoutSeconds": 3600}
    return get_predict_async_client(endpoint_name).predict_async(data=data,
                                                                 initial_args=initial_args,
                                                                 inference_id=inference_id)


def async_inference(payload, job: InferenceJob, endpoint_name):
    prediction = predictor_predict_async(endpoint_name=endpoint_name,
                                         data=payload.__dict__,
                                         inference_id=job.InferenceJobId)
    logger.info(f"prediction: {prediction}")
    output_path = prediction.output_path

    # update the ddb job status to 'inprogress' and save to ddb
    job.status = 'inprogress'
    job.params['output_path'] = output_path
    ddb_service.put_items(inference_table_name, job.__dict__)

    data = {
        'inference': {
            'inference_id': job.InferenceJobId,
            'status': job.status,
            'endpoint_name': endpoint_name,
            'output_path': output_path
        }
    }

    return accepted(data=data)
