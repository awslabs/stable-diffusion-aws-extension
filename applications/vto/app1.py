import os
import random

import gradio as gr


def image_mod(image):
    return image.rotate(45)


def fake_gan():
    model_images = []
    for root, dirs, files in os.walk("./clothes/cloth"):
        for file in files:
            if file.endswith(".png"):
                model_images.append(os.path.join(root, file))
    images = [
        (random.choice(
            model_images
        ), f"Model {i}")
        for i in range(20)
    ]

    print(images)

    return images


with gr.Blocks(title="VTO") as demo:
    gallery = gr.Gallery(
        label="Generated images",
        show_label=False,
        elem_id="gallery",
        columns=[7],
        rows=[3],
        object_fit="contain",
        height="auto")
    btn = gr.Button("Generate images", scale=0)
    btn.click(fake_gan, None, gallery)

    clothes_images = []
    for root, dirs, files in os.walk("./person/model"):
        for file in files:
            if file.endswith(".png"):
                clothes_images.append(os.path.join(root, file))

    # demo2 = gr.Interface(
    #     image_mod,
    #     gr.Image(type="pil"),
    #     "image",
    #     flagging_options=["blurry", "incorrect", "other"],
    #     examples=clothes_images,
    # )

if __name__ == "__main__":
    demo.launch(share=True)
