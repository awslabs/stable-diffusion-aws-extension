import base64
import logging
import os
from datetime import datetime
from io import BytesIO

import gradio as gr
from PIL import Image
from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.serializers import JSONSerializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def base64_to_image(base64_string):
    img_data = base64.b64decode(base64_string)
    img = Image.open(BytesIO(img_data))
    return img


def real_time_inference(payload, endpoint_name):
    predictor = Predictor(endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    start_time = datetime.now()
    prediction_sync = predictor.predict(data=payload.__dict__,
                                        inference_id=job.InferenceJobId,
                                        )
    logger.info(prediction_sync)

    if 'error' in prediction_sync:
        if 'detail' in prediction_sync:
            raise gr.Error(prediction_sync['detail'])
        raise gr.Error(str(prediction_sync))

    end_time = datetime.now()
    cost_time = (end_time - start_time).total_seconds()
    logger.info(f"Real-time inference cost_time: {cost_time}")

    print(prediction_sync)


def get_images(path: str):
    images = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".png"):
                image = os.path.join(root, file)
                name = image.split('/')[-1].rstrip('.png')
                images.append((image, name))

    return images


clothes_images = get_images("./clothes/cloth")
models_images = get_images("./person/model")

with gr.Blocks(title="VTO") as demo:
    gr.HTML("<h1>Virtual try-on</h1>")

    clothes = gr.Gallery(
        label="Clothes",
        show_label=True,
        elem_id="clothes_gallery",
        columns=[8],
        rows=[1],
        object_fit="contain",
        value=clothes_images,
        height="100px")

    with gr.Row():
        model = gr.Gallery(
            label="Models",
            show_label=True,
            elem_id="models_gallery",
            columns=[1],
            rows=[5],
            object_fit="contain",
            value=models_images,
            scale=1
        )

        result_image = gr.Image(
            type="pil",
            label="Try-on Result",
            show_label=True,
            elem_id="result_image",
            interactive=False,
            scale=4,
            shape=(None, 200),
            fixed=True,
            height="100px"
        )

    current_cloth = None
    current_model = None


    def get_result():
        global current_cloth
        global current_model
        if current_cloth is None or current_model is None:
            return
        data = {
            "cloth_file": current_cloth[0],
            "cloth_base64": get_image_base64(current_cloth[0]),
            "cloth_name": current_cloth[1],

            "model_file": current_model[0],
            "model_base64": get_image_base64(current_model[0]),
            "model_name": current_model[1]
        }
        print(data)

        # TODO: call the sagemaker
        res = get_image_base64(current_model[0])

        return base64_to_image(res)


    def get_image_base64(image_path):
        with open(image_path, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode('utf-8')
        return encoded_string


    def on_select_clothes(evt: gr.SelectData):
        global current_cloth
        current_cloth = clothes_images[evt.index]
        return get_result()


    def on_select_models(evt: gr.SelectData):
        global current_model
        current_model = models_images[evt.index]
        return get_result()


    clothes.select(on_select_clothes, None, result_image)
    model.select(on_select_models, None, result_image)

if __name__ == "__main__":
    demo.launch(share=False, enable_queue=True)
