import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time
import os
from gradio.processing_utils import encode_pil_to_base64
import sys
import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
import json
import uuid

from sagemaker.predictor import Predictor
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer
from fastapi.responses import JSONResponse

s3_resource = boto3.resource('s3')
s3_client = boto3.client('s3')


def get_bucket_and_key(s3uri):
    pos = s3uri.find('/', 5)
    bucket = s3uri[5 : pos]
    key = s3uri[pos + 1 : ]
    return bucket, key


used_models = {
                'space_free_size': 400000000.0,  # sys.float_info.max
              }

Stable_diffusion_list = [{'s3': 's3://sd-ui-data-bucket-20230928/Stable-diffusion/checkpoint/custom/753c7a30-17aa-4d5c-bb16-faaac0643122', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'majicmixRealistic_v7.safetensors', 'type': 'Stable-diffusion'},
                         {'s3': 's3://sd-ui-data-bucket-20230928/Stable-diffusion/checkpoint/custom/3cfc3a91-e21e-4837-addc-ee74b969280c', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'epicphotogasm_x.safetensors', 'type': 'Stable-diffusion'},
                         {'s3': 's3://sd-ui-data-bucket-20230928/Stable-diffusion/checkpoint/custom/465f562e-de48-4485-950b-18da59f99a00', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'yayoiMix_v25.safetensors', 'type': 'Stable-diffusion'},
                         {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/588cb29d-95d7-40ed-86c3-b69f94f8d1a1', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'sd_xl_base_1.0.safetensors', 'type': 'Stable-diffusion'}]

VAE_list = [{'s3': 's3://sd-ui-data-bucket-20230928/VAE/checkpoint/custom/0aa260b8-e849-42d1-a2cf-70db6e3d5eb8', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'vae-ft-mse-840000-ema-pruned.safetensors', 'type': 'VAE'}]           



start_time = time.time()
used_models_3 = used_models.copy()
# used_models_3['Stable-diffusion'] = [Stable_diffusion_list[0]]
test_model = [{'s3': 's3://aoyu-webui-uw2', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'v1-5-pruned-emaonly.safetensors', 'type': 'Stable-diffusion'}]
used_models_3['Stable-diffusion'] = test_model

payload = {
            "task": "txt2img",
            "username": "test",
            "models": used_models_3,
            # "param_s3": 's3://aoyu-webui-uw2/txt2img.json'
            "param_s3": 's3://aoyu-webui-uw2/txt2img/infer_v2/fbbd9c22-3e50-40a9-8fe2-a4b950768bdc/api_param.json'
        }
#txt2img_debug
# endpoint_name = 'infer-endpoint-api-test'
endpoint_name = 'infer-endpoint-api-test'
# endpoint_name = 'infer-endpoint-test-private-no-sd15-model'

predictor = Predictor(endpoint_name)

# adjust time out time to 1 hour
initial_args = {"InvocationTimeoutSeconds": 3600}
inference_id = str(uuid.uuid4())
predictor = AsyncPredictor(predictor, name=endpoint_name)
predictor.serializer = JSONSerializer()
predictor.deserializer = JSONDeserializer()
prediction = predictor.predict_async(data=payload, initial_args=initial_args, inference_id=inference_id)
output_path = prediction.output_path

from sagemaker.async_inference.waiter_config import WaiterConfig
print(f"Response object: {prediction}")
print(f"Response output path: {output_path}")
print("Start Polling to get response:")

import time

start = time.time()

config = WaiterConfig(
  max_attempts=100, #  number of attempts
  delay=0.5 #  time in seconds to wait between attempts
  )

prediction.get_result(config)

print(f"Time taken: {time.time() - start}s")

bucket, key = get_bucket_and_key(output_path)
print(bucket)
print(key)
obj = s3_resource.Object(bucket, key)
body = obj.get()['Body'].read().decode('utf-8')
json_body = json.loads(body)

id = 0
for image_base64 in json_body['images']:
    image = Image.open(io.BytesIO(base64.b64decode(image_base64)))
    image.save(f'output_endpoint_{endpoint_name}_eulera_%d.png'%(id))
    id += 1



