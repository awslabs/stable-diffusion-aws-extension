import json
import io
import base64
from PIL import Image
import time
import json
import uuid

from sagemaker.predictor import Predictor
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer

start_time = time.time()

payload_path = '../vto_input.json'
with open(payload_path, 'r') as f:
    param_s3 = json.load(f)

task_name = "vto" # "txt2img" lcm_lora_pipeline
payload = {
        "task": task_name,
        "username": "xiaoyu",
        "param_s3": param_s3
    }
#txt2img_debug
endpoint_name = 'infer-endpoint-aigc-app-vto'

predictor = Predictor(endpoint_name)

# adjust time out time to 1 hour
inference_id = str(uuid.uuid4())
predictor.serializer = JSONSerializer()
predictor.deserializer = JSONDeserializer()
prediction = predictor.predict(data=payload, inference_id=inference_id)

# print(f"Response object: {prediction}")

r = prediction

id = 0
for image_base64 in r['images_tryon']:
    image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",",1)[0])))
    image.save('./results/output_tryon_%d.png'%(id))
    id += 1

for image_base64 in r['images_warp']:
    image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",",1)[0])))
    image.save('./results/output_warp_%d.png'%(id))
    id += 1

print(f"Time taken: {time.time() - start_time}s")



