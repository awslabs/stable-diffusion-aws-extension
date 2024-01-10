import json
import logging
import os
from datetime import datetime

from sagemaker import Predictor
from sagemaker.async_inference import WaiterConfig
from sagemaker.deserializers import JSONDeserializer
from sagemaker.exceptions import PollingTimeoutError
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import accepted
from libs.data_types import InferenceJob, InvocationsRequest

inference_table_name = os.environ.get('DDB_INFERENCE_TABLE_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

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

    logger.info(f"payload: {payload}")

    # start async inference
    predictor = Predictor("realtime")
    initial_args = {"InvocationTimeoutSeconds": 3600}
    # predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    output_path = None
    start_time = datetime.now()
    try:
        prediction_sync = predictor.predict(data=payload.__dict__,
                                            inference_id=inference_id,
                                            )
        logger.info(f"prediction_sync: {prediction_sync}")
    except PollingTimeoutError as e:
        print(e.kwargs)
        print(e.kwargs.get('message'))
        print(e.kwargs.get('seconds'))
        output_path = e.kwargs.get('output_path')
    except Exception as e:
        print(e)
        raise e
    end_time = datetime.now()
    cost_time = (end_time - start_time).total_seconds()
    logger.info(f"cost_time: {cost_time}")
    # prediction = predictor.predict_async(data=payload.__dict__, initial_args=initial_args, inference_id=inference_id)
    # logger.info(f"prediction: {prediction}")
    # output_path = prediction.output_path

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
