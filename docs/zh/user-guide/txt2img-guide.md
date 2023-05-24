





# 利用txt2img进行推理

* ### 上传推理所需模型

    1. 打开**Amazon SageMaker**面板
    
        ![Sagemaker Inference面板](../images/sagemaker-panel.png)
    
    2. 对于需要上传的模型，在 **Upload Models to Cloud**上面输入对应模型的绝对地址（可以填写一个或者多个），并且点击上传按钮。可以通过终端看到，上传逻辑是基于multi-part实现

        ![Upload models](../images/upload-models.png)
    
    3. 打开**txt2img**下面的**Amazon SageMaker Inference**面板

        ![sagemer inference txt2img](../images/txt2img-sagemaker-panel.png)
    

    4. 点击**Stable Diffusion Checkpoint**和**Extra Networks for Cloud Inference**旁边的刷新按钮，以查看哪些已经存储在s3上的模型可以用于txt2img的推理
![Refresh models](../images/refresh-models.png)

* ### 输入推理所需参数

    1. 点击**Select Cloud SageMaker Endpoint**旁边的刷新按钮，选择处于**InService**状态的推理节点。注意，如果选择处于其他状态的推理节点，或者没有选择推理节点，点击**Generate on Cloud**会报错。
    2. 选择合适的**Stable Diffusion Checkpoint**，比如这里选择**v1-5-pruned-emaonly.safetensors**。注意，所有的模型都可以多选。
    3. 输入提示词**a cute dog**等其他需要的参数，然后点击**Generate on Cloud**。 
    ![generate on cloud](../images/generate-on-cloud-txt2img.png)
    4. 这时候点击**Inference Job IDs**旁边的刷新按钮，可以看到新产生一条记录，格式为**推理时间->inference id** (整个列表也会按照推理时间进行排序)
    ![refresh inference job id](../images/refresh-inference-id.png)
    5. 当切换到对应的inference id并且推理结束后，会在右上角看到推理的结果，包括图片，提示词以及推理的参数等。在此基础上，可以点击**Save**或者**Send to img2img**等
    ![generate results](../images/generate-results.png)



# Controlnet的使用方法

* ### openpose的使用方式
    1. 打开ControlNet面板，勾选**Enabel**，选择**Preprocessor**为**openpose**，同时上传图片。
    
        ![Controlnet-openpose-prepare](../images/controlnet-openpose-prepare.png)
    
    2. 在**Amazon SageMaker Inference**面板的里面选择**Stable Diffusion Checkpoint**和**ControlNet-Model**。比如
    这里是**v1-5-pruned-emaonly.safetensors**和**control_openpose-fp16.safetensors**。保留之前的提示词**a cute dog**
    ，然后点击**Generate on Cloud**。

        ![Choose-controlnet-model](../images/choose-controlnet-model.png)

    3. 这时候点击**Inference Job IDs**旁边的刷新按钮，可以看到新产生一条记录，格式为**推理时间->inference id** (整个列表也会按照推理时间进行排序)
    ![refresh inference job id-controlnet](../images/refresh-inference-id-controlnet.png)

    4. 当切换到对应的inference id并且推理结束后，会在右上角看到推理的结果，包括图片，提示词以及推理的参数等。在此基础上，可以点击**Save**或者**Send to img2img**等
    ![generate results controlnet](../images/cute-dog-controlnet.png)