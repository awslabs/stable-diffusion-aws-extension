import logging
import os

from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import accepted
from libs.data_types import InferenceJob, InvocationsRequest

inference_table_name = os.environ.get('DDB_INFERENCE_TABLE_NAME')

logger = logging.getLogger('inference_v2')
ddb_service = DynamoDbUtilsService(logger=logger)


def handler(event, _):
    _filter = {}
    inference_id = event['pathParameters']['id']

    # get the inference job from ddb by job id
    inference_raw = ddb_service.get_item(inference_table_name, {
        'InferenceJobId': inference_id
    })

    assert inference_raw is not None and len(inference_raw) > 0
    inference_job = InferenceJob(**inference_raw)
    endpoint_name = inference_job.params['sagemaker_inference_endpoint_name']
    models = {}
    if 'used_models' in inference_job.params:
        models = {
            "space_free_size": 4e10,
            **inference_job.params['used_models'],
        }

    payload = InvocationsRequest(
        task=inference_job.taskType,
        username="test",
        models=models,
        param_s3=inference_job.params['input_body_s3']
    )

    # start async inference
    predictor = Predictor(endpoint_name)
    initial_args = {"InvocationTimeoutSeconds": 3600}
    predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    prediction = predictor.predict_async(data=payload.__dict__, initial_args=initial_args, inference_id=inference_id)
    output_path = prediction.output_path

    # update the ddb job status to 'inprogress' and save to ddb
    inference_job.status = 'inprogress'
    inference_job.params['output_path'] = output_path
    ddb_service.put_items(inference_table_name, inference_job.__dict__)

    data = {
        'inference': {
            'inference_id': inference_id,
            'status': inference_job.status,
            'endpoint_name': endpoint_name,
            'output_path': output_path
        }
    }

    return accepted(data=data)
