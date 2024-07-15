## Features

This solution supports the cloud-based operations of the following 3 projects.

| **Project**  | **Supported Version** | **Note**|
| ------------- | ------------- | ------------- |
|Stable Diffusion WebUI| V 1.8.0| The default supported native/third-party extensions are listed in the table below. |
|ComfyUI| 605e64f6d3da44235498bf9103d7aab1c95ef211|The custom nodes that require cloud-based inference support can be packaged and uploaded to the cloud in one click using the template publishing feature provided by this solution. Therefore, this solution does not include built-in support for custom nodes; users can flexibly choose to install and package them for upload. |
|Kohya_ss|V0.8.3|Support LoRa model training based on SD 1.5 and SDXL.|

Below please find the native features/third-party extensions supported by this solution for Stable Diffusion WebUI. Other extensions can be supported through [BYOC (Bring Your Own Container)]((../developer-guide/byoc.md)).

| **Feature**  | **Supported Version** | **Note** |
| ------------- | ------------- | ------------- |
| [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.8.0 | Support LCM as official sampler, SDXL-Inpaint, etc|
| [img2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.8.0  | Support all features except batch|
| [txt2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.8.0  | |
| [LoRa](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.2.1  | |
| [ControlNet](https://github.com/Mikubill/sd-webui-controlnet){:target="_blank"}  | V1.1.410  | Support SDXL + ControlNet Inference|
| [Tiled Diffusion & VAE](https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git){:target="_blank"}  | f9f8073e64f4e682838f255215039ba7884553bf  |
| [ReActor for Stable Diffusion](https://github.com/Gourieff/sd-webui-reactor{:target="_blank"}) | 0.6.1 |
| [Extras](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.8.0  | API|
| [rembg](https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git){:target="_blank"}  | 3d9eedbbf0d585207f97d5b21e42f32c0042df70  | API |
| [kohya_ss](https://github.com/bmaltais/kohya_ss){:target="_blank"}  |   | 

## Benefits
* **Convenient Installation**: This solution leverages CloudFormation for easy deployment of AWS middleware. Combined with the installation of the native Stable Diffusion WebUI (WebUI) features and third-party extensions, users can quickly utilize Amazon SageMaker's cloud resources for inference, training and finetuning tasks.

* **Community Native**: This solution is implemented as an extension, allowing users to seamlessly use their existing WebUI without any changes. Additionally, the solution's code is open source and follows a non-intrusive design, enabling users to keep up with community-related feature iterations, such as popular plugins like ControlNet, and LoRa.

* **High Scalability**: This solution decouples the WebUI interface from the backend, allowing the WebUI to launch on supported terminals without GPU restrictions. Existing training, inference, and other tasks can be migrated to Amazon SageMaker through the provided extension functionalities, providing users with elastic computing resources, cost reduction, flexibility, and scalability.
















