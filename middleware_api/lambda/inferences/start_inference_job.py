import base64
import io
import json
import logging
import os
from datetime import datetime

import boto3
from PIL import Image
from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import accepted, bad_request
from get_inference_job import get_infer_data
from libs.data_types import InferenceJob, InvocationsRequest
from libs.enums import EndpointType

S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
inference_table_name = os.environ.get('INFERENCE_JOB_TABLE')

s3_client = boto3.client('s3')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_client = boto3.resource('dynamodb')

ddb_service = DynamoDbUtilsService(logger=logger)
inference_table = ddb_client.Table(inference_table_name)


def upload_file_to_s3(file_name, bucket, directory=None, object_name=None):
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Add the directory to the object_name
    if directory:
        object_name = f"{directory}/{object_name}"

    # Upload the file
    try:
        s3_client.upload_file(file_name, bucket, object_name)
        print(f"File {file_name} uploaded to {bucket}/{object_name}")
    except Exception as e:
        print(f"Error occurred while uploading {file_name} to {bucket}/{object_name}: {e}")
        return False
    return True


def decode_base64_to_image(encoding):
    if encoding.startswith("data:image/"):
        encoding = encoding.split(";")[1].split(",")[1]
    return Image.open(io.BytesIO(base64.b64decode(encoding)))


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
    else:
        return async_inference(payload, job, endpoint_name)


def real_time(payload, job: InferenceJob, endpoint_name):
    predictor = Predictor(endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    try:
        start_time = datetime.now()
        prediction_sync = predictor.predict(data=payload.__dict__,
                                            inference_id=job.InferenceJobId,
                                            )
        logger.info(prediction_sync)
        end_time = datetime.now()
        cost_time = (end_time - start_time).total_seconds()
        logger.info(f"inference cost_time: {cost_time}")

        handle_sagemaker_out(job, prediction_sync, endpoint_name)

        return get_infer_data(job.InferenceJobId)
    except Exception as e:
        print(e)
        return bad_request(str(e))


def async_inference(payload, job: InferenceJob, endpoint_name):
    predictor = Predictor(endpoint_name)
    initial_args = {"InvocationTimeoutSeconds": 3600}
    predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    prediction = predictor.predict_async(data=payload.__dict__, initial_args=initial_args,
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


def handle_sagemaker_out(job: InferenceJob, json_body, endpoint_name):
    update_inference_job_table(job.InferenceJobId, 'completeTime', str(datetime.now()))
    try:

        if job.taskType in ["interrogate_clip", "interrogate_deepbooru"]:
            caption = json_body['caption']
            # Update the DynamoDB table for the caption
            inference_table.update_item(
                Key={
                    'InferenceJobId': job.InferenceJobId
                },
                UpdateExpression='SET caption=:f',
                ExpressionAttributeValues={
                    ':f': caption,
                }
            )
        elif job.taskType in ["txt2img", "img2img"]:
            # save images
            for count, b64image in enumerate(json_body["images"]):
                image = decode_base64_to_image(b64image).convert("RGB")
                output = io.BytesIO()
                image.save(output, format="JPEG")
                # Upload the image to the S3 bucket
                s3_client.put_object(
                    Body=output.getvalue(),
                    Bucket=S3_BUCKET_NAME,
                    Key=f"out/{job.InferenceJobId}/result/image_{count}.jpg"
                )
                # Update the DynamoDB table
                inference_table.update_item(
                    Key={
                        'InferenceJobId': job.InferenceJobId
                    },
                    UpdateExpression='SET image_names = list_append(if_not_exists(image_names, :empty_list), :new_image)',
                    ExpressionAttributeValues={
                        ':new_image': [f"image_{count}.jpg"],
                        ':empty_list': []
                    }
                )

            # save parameters
            inference_parameters = {}
            inference_parameters["parameters"] = json_body["parameters"]
            inference_parameters["info"] = json_body["info"]
            inference_parameters["endpont_name"] = endpoint_name
            inference_parameters["inference_id"] = job.InferenceJobId

            json_file_name = f"/tmp/{job.InferenceJobId}_param.json"

            with open(json_file_name, "w") as outfile:
                json.dump(inference_parameters, outfile)

            upload_file_to_s3(json_file_name, S3_BUCKET_NAME, f"out/{job.InferenceJobId}/result",
                              f"{job.InferenceJobId}_param.json")
            update_inference_job_table(job.InferenceJobId, 'inference_info_name', json_file_name)

        update_inference_job_table(job.InferenceJobId, 'status', 'succeed')
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        update_inference_job_table(job.InferenceJobId, 'status', 'failed')
        raise e


def update_inference_job_table(inference_id, key, value):
    # Update the inference DDB for the job status
    response = inference_table.get_item(
        Key={
            "InferenceJobId": inference_id,
        })
    inference_resp = response['Item']
    if not inference_resp:
        raise Exception(f"Failed to get the inference job item with inference id: {inference_id}")

    response = inference_table.update_item(
        Key={
            "InferenceJobId": inference_id,
        },
        UpdateExpression=f"set #k = :r",
        ExpressionAttributeNames={'#k': key},
        ExpressionAttributeValues={':r': value},
        ReturnValues="UPDATED_NEW"
    )
