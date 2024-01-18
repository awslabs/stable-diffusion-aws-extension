#from options.train_options import TrainOptions
import os
import numpy as np
import uuid
from PIL import Image, ImageDraw
import io
import base64
import time
import json

from utils.mme_utils import image_to_base64

from sagemaker.predictor import Predictor
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer
# from inference.inference_api import tryon_api
  
import pathlib
base_path = pathlib.Path(__file__).parent.resolve()

# demo_cloth_dir = f'/home/ubuntu/virtual_try_on/GP-VTON/demo_samples/clothes'
# demo_cloth_dir = f'/home/ubuntu/virtual_try_on/GP-VTON/demo_samples/clothes'
# demo_person_dir = '/home/ubuntu/virtual_try_on/GP-VTON/demo_samples/person'
# warproot = '/home/ubuntu/virtual_try_on/GP-VTON/demo_samples/warped_clothes'
# try_on_result_dir = '/home/ubuntu/virtual_try_on/GP-VTON/demo_samples/try_on_results'

demo_cloth_dir = f'{base_path}/clothes'
demo_person_dir = f'{base_path}/person'
warproot = f'{base_path}/warped_clothes'
try_on_result_dir = f'{base_path}/try_on_results'

def vto_realtime_inference(payload):

    start_time = time.time()

    # payload_path = '../vto_input.json'
    # with open(payload_path, 'r') as f:
    #     param_s3 = json.load(f)
    param_s3 = payload

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
        tryon_image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",",1)[0])))
        tryon_image.save(f'{base_path}/results/output_tryon_%d.png'%(id))
        id += 1

    for image_base64 in r['images_warp']:
        image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",",1)[0])))
        image.save(f'{base_path}/results/output_warp_%d.png'%(id))
        id += 1

    run_time = time.time() - start_time

    return tryon_image, run_time


def vto_update_payload(current_cloth, current_model):
    person_id = f"{current_model[1]}.png"
    cloth_id = f"{current_cloth[1]}.png"
    # person_id = 'wenmeng1.png'
    # cloth_id = '10062_00.png'

    payload={}

    ###########################################################
    # person image
    P_path = os.path.join(demo_person_dir, 'model', person_id)
    person_img = Image.open(P_path).convert('RGB')
    payload['person_img'] = image_to_base64(person_img)

    # person 2d pose
    pose_path = P_path.replace('/model/', '/openpose_json/')[:-4]+'_keypoints.json'
    with open(pose_path, 'r') as f:
        datas = json.load(f)
    pose_data = np.array(datas['people'][0]['pose_keypoints_2d']).reshape(-1,3)
    payload['pose_data'] = datas['people'][0]['pose_keypoints_2d']

    # person 3d pose
    densepose_path = P_path.replace('/model/', '/densepose/')[:-4]+'.png'
    dense_mask = Image.open(densepose_path).convert('L')
    payload['dense_mask'] = image_to_base64(dense_mask)

    # person parsing
    parsing_path = P_path.replace('/model/', '/parse-bytedance/')[:-4]+'.png'
    person_parsing = Image.open(parsing_path).convert('L')
    payload['person_parsing'] = image_to_base64(person_parsing)


    ### clothes
    C_path = os.path.join(demo_cloth_dir, 'cloth', cloth_id)
    cloth_img = Image.open(C_path).convert('RGB')
    payload['cloth_img'] = image_to_base64(cloth_img)


    CM_path = C_path.replace('/cloth/', '/cloth_mask-bytedance/')[:-4]+'.png'
    cloth_mask = Image.open(CM_path).convert('L')
    payload['cloth_mask'] = image_to_base64(cloth_mask)


    cloth_parsing_path = C_path.replace('/cloth/', '/cloth_parse-bytedance/')[:-4]+'.png'
    cloth_parsing = Image.open(cloth_parsing_path).convert('L')
    payload['cloth_parsing'] = image_to_base64(cloth_parsing)

    return payload

    # output_json = open('vto_input.json', 'w')
    # json.dump(payload, output_json)
    
    ###########################################################

    #### api input : person_img, cloth_img, pose_data, dense_mask, person_parsing, cloth_mask, cloth_parsing
    #### api output: tryon_result, warp_result
    # tryon_result, warp_result = tryon_api(person_img, cloth_img, pose_data, dense_mask, person_parsing, cloth_mask, cloth_parsing)

    # save_path = warproot +'/'+person_id.split('.')[0]+'___'+cloth_id.split('.')[0]+'.png'
    # Image.fromarray(warp_result).save(save_path)

    # save_path = try_on_result_dir + '/'+person_id.split('.')[0]+'___'+cloth_id.split('.')[0]+'.png'
    # Image.fromarray(tryon_result).save(save_path)

def main(current_cloth, current_model):
    payload = vto_update_payload(current_cloth, current_model)
    return payload

if __name__ == '__main__':
    main()  