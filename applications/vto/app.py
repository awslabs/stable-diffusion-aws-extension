import base64
import logging
import os
import time
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
    prediction_sync = predictor.predict(data=payload)
    logger.info(prediction_sync)

    if 'error' in prediction_sync:
        if 'detail' in prediction_sync:
            raise gr.Error(prediction_sync['detail'])
        raise gr.Error(str(prediction_sync))

    end_time = datetime.now()
    cost_time = (end_time - start_time).total_seconds()
    logger.info(f"Real-time inference cost_time: {cost_time}")

    print(prediction_sync)


def get_image_base64(image_path):
    with open(image_path, "rb") as f:
        encoded_string = base64.b64encode(f.read()).decode('utf-8')
    return encoded_string


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

title = "Virtual Try-on"
with gr.Blocks(title=title) as demo:
    gr.HTML(f"<h1>{title}</h1>")

    clothes = gr.Gallery(
        label="Clothes",
        show_label=True,
        elem_id="clothes_gallery",
        columns=10,
        rows=1,
        object_fit="fill",
        value=clothes_images,
        allow_preview=False,
        height=155
    )

    with gr.Row():
        model = gr.Gallery(
            label="Models",
            show_label=True,
            elem_id="models_gallery",
            columns=1,
            rows=5,
            object_fit="contain",
            value=models_images,
            scale=1,
            allow_preview=False,
            height=670,
        )

        with gr.Column(scale=4):
            gr.Radio(
                choices=["Option1", "Option2"],
                label="Try-on Result",
                show_label=False,
                value="Try-on Result",
                elem_id="select_radio",
            )
            result_image = gr.Image(
                type="pil",
                label="Try-on Result",
                show_label=True,
                elem_id="result_image",
                interactive=False,
                shape=(None, 200),
                height=600,
            )

    result_text = gr.TextArea(show_label=True, label="Try-on Result", interactive=False, elem_id="result_text")
    current_cloth = None
    current_model = None


    def get_result():
        global current_cloth
        global current_model

        if current_cloth is None:
            gr.Warning("Please select a cloth to inference.")
            return None, None
        if current_model is None:
            gr.Warning("Please select a model to inference.")
            return None, None

        inference_payload = {
            "cloth_file": current_cloth[0],
            "cloth_base64": get_image_base64(current_cloth[0]),
            "cloth_name": current_cloth[1],

            "model_file": current_model[0],
            "model_base64": get_image_base64(current_model[0]),
            "model_name": current_model[1]
        }
        print(inference_payload)

        # TODO: call the sagemaker real-time inference endpoint
        res = get_image_base64(current_model[0])

        time.sleep(1)
        result_text = current_model

        return base64_to_image(res), result_text


    def on_select_clothes(evt: gr.SelectData):
        global current_cloth
        current_cloth = clothes_images[evt.index]
        return get_result()


    def on_select_models(evt: gr.SelectData):
        global current_model
        current_model = models_images[evt.index]
        return get_result()


    clothes.select(on_select_clothes, None, [result_image, result_text])
    model.select(on_select_models, None, [result_image, result_text])

if __name__ == "__main__":
    demo.queue()
    demo.launch(share=False, server_name="0.0.0.0")
