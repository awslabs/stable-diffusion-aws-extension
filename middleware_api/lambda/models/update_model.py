import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

from botocore.exceptions import ClientError
from sagemaker import Predictor
from sagemaker.predictor_async import AsyncPredictor

from libs.common_tools import complete_multipart_upload, DecimalEncoder
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request, internal_server_error
from libs.data_types import Model, CreateModelStatus, CheckPoint, CheckPointStatus

model_table = os.environ.get('DYNAMODB_TABLE')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
endpoint_name = os.environ.get('SAGEMAKER_ENDPOINT_NAME')

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class PutModelEvent:
    status: str
    multi_parts_tags: Dict[str, Any]


def handler(raw_event, context):
    logger.info(json.dumps(raw_event))
    event = PutModelEvent(**json.loads(raw_event['body']))

    model_id = raw_event['pathParameters']['id']

    try:
        raw_model_job = ddb_service.get_item(table=model_table, key_values={'id': model_id})
        if raw_model_job is None:
            return bad_request(message=f'create model with id {model_id} is not found')

        model_job = Model(**raw_model_job)
        raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
            'id': model_job.checkpoint_id,
        })
        if raw_checkpoint is None:
            return bad_request(message=f'create model ckpt with id {model_id} is not found')

        ckpt = CheckPoint(**raw_checkpoint)
        if ckpt.checkpoint_status == ckpt.checkpoint_status.Initial:
            complete_multipart_upload(ckpt, event.multi_parts_tags)
            ddb_service.update_item(
                table=checkpoint_table,
                key={'id': ckpt.id},
                field_name='checkpoint_status',
                value=CheckPointStatus.Active.value
            )

        data = _exec(model_job, CreateModelStatus[event.status])
        ddb_service.update_item(
            table=model_table,
            key={'id': model_job.id},
            field_name='job_status',
            value=event.status
        )
        return ok(data=data)
    except ClientError as e:
        logger.error(e)
        return internal_server_error(message=str(e))


def _exec(model_job: Model, action: CreateModelStatus):
    if model_job.job_status == CreateModelStatus.Creating and \
            (action != CreateModelStatus.Fail or action != CreateModelStatus.Complete):
        raise Exception(f'model creation job is currently under progress, so cannot be updated')

    if action == CreateModelStatus.Creating:
        model_job.job_status = action
        raw_chkpt = ddb_service.get_item(table=checkpoint_table, key_values={'id': model_job.checkpoint_id})
        if raw_chkpt is None:
            raise Exception(f'model related checkpoint with id {model_job.checkpoint_id} is not found')

        checkpoint = CheckPoint(**raw_chkpt)
        checkpoint.checkpoint_status = CheckPointStatus.Active
        ddb_service.update_item(
            table=checkpoint_table,
            key={'id': checkpoint.id},
            field_name='checkpoint_status',
            value=CheckPointStatus.Active.value
        )
        return create_sagemaker_inference(job=model_job, checkpoint=checkpoint)
    elif action == CreateModelStatus.Initial:
        raise Exception('please create a new model creation job for this,'
                        f' not allowed overwrite old model creation job')
    else:
        # todo: other action
        raise NotImplemented


def create_sagemaker_inference(job: Model, checkpoint: CheckPoint):
    payload = {
        "task": "db-create-model",  # router
        "param_s3": "",
        "db_create_model_payload": json.dumps({
            "s3_output_path": job.output_s3_location,  # output object
            "s3_input_path": checkpoint.s3_location,
            "ckpt_names": checkpoint.checkpoint_names,
            "param": job.params,
            "job_id": job.id
        }, cls=DecimalEncoder),
    }

    from sagemaker.serializers import JSONSerializer
    from sagemaker.deserializers import JSONDeserializer

    predictor = Predictor(endpoint_name)

    predictor = AsyncPredictor(predictor, name=job.id)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    prediction = predictor.predict_async(data=payload, inference_id=job.id)
    output_path = prediction.output_path

    return {
        'job': {
            'output_path': output_path,
            'id': job.id,
            'endpointName': endpoint_name,
            'jobStatus': job.job_status.value,
            'jobType': job.model_type
        }
    }
