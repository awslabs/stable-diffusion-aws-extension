import json
import logging
import os
from datetime import datetime

from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import accepted, bad_request
from get_inference_job import get_infer_data
from inference_libs import parse_result, update_inference_job_table
from libs.data_types import InferenceJob, InvocationsRequest
from libs.enums import EndpointType

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

inference_table_name = os.environ.get('INFERENCE_JOB_TABLE')

ddb_service = DynamoDbUtilsService(logger=logger)


def handler(event, _):
    logger.info(json.dumps(event))
    _filter = {}
    inference_id = event['pathParameters']['id']

    # get the inference job from ddb by job id
    inference_raw = ddb_service.get_item(inference_table_name, {
        'InferenceJobId': inference_id
    })

    assert inference_raw is not None and len(inference_raw) > 0
    job = InferenceJob(**inference_raw)
    endpoint_name = job.params['sagemaker_inference_endpoint_name']
    models = {}
    if 'used_models' in job.params:
        models = {
            "space_free_size": 4e10,
            **job.params['used_models'],
        }

    payload = InvocationsRequest(
        task=job.taskType,
        username="test",
        models=models,
        param_s3=job.params['input_body_s3']
    )

    logger.info(f"payload: {payload}")

    update_inference_job_table(job.InferenceJobId, 'startTime', str(datetime.now()))

    if job.inference_type == EndpointType.RealTime.value:
        return real_time(payload, job, endpoint_name)

    return async_inference(payload, job, endpoint_name)


def real_time(payload, job: InferenceJob, endpoint_name):
    predictor = Predictor(endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    try:
        start_time = datetime.now()
        sagemaker_out = predictor.predict(data=payload.__dict__,
                                          inference_id=job.InferenceJobId,
                                          )
        logger.info(sagemaker_out)

        if 'error' in sagemaker_out:
            update_inference_job_table(job.InferenceJobId, 'sagemakerRaw', str(sagemaker_out))
            raise Exception(str(sagemaker_out))

        end_time = datetime.now()
        cost_time = (end_time - start_time).total_seconds()
        logger.info(f"Real-time inference cost_time: {cost_time}")

        parse_result(sagemaker_out, job.InferenceJobId, job.taskType, endpoint_name)

        return get_infer_data(job.InferenceJobId)
    except Exception as e:
        print(e)
        return bad_request(message=str(e))


def async_inference(payload, job: InferenceJob, endpoint_name):
    predictor = Predictor(endpoint_name)
    initial_args = {"InvocationTimeoutSeconds": 3600}
    predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    prediction = predictor.predict_async(data=payload.__dict__,
                                         initial_args=initial_args,
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
