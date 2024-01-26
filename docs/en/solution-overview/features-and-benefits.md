## Features

This solution supports the cloud-based operations of the following native features/third-party extensions of Stable Diffusion WebUI:

| **Feature**  | **Supported Version** | **Note** |
| ------------- | ------------- | ------------- |
| [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.7.0 | Support Stable Diffusion XL 1.0 and refiner|
| [img2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.7.0  | Support all features except batch|
| [txt2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.7.0  | |
| [LoRa](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.2.1  | |
| [ControlNet](https://github.com/Mikubill/sd-webui-controlnet){:target="_blank"}  | V1.1.410  | Support SDXL + ControlNet Inference|
| [Tiled Diffusion & VAE](https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git){:target="_blank"}  | f9f8073e64f4e682838f255215039ba7884553bf  |
| [Extras](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}  | V1.7.0  | API|
| [rembg](https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git){:target="_blank"}  | 3d9eedbbf0d585207f97d5b21e42f32c0042df70  | API

## Benefits
* **Convenient Installation**: This solution leverages CloudFormation for easy deployment of AWS middleware. Combined with the installation of the native Stable Diffusion WebUI (WebUI) features and third-party extensions, users can quickly utilize Amazon SageMaker's cloud resources for inference, training and finetuning tasks.

* **Community Native**: This solution is implemented as an extension, allowing users to seamlessly use their existing WebUI without any changes. Additionally, the solution's code is open source and follows a non-intrusive design, enabling users to keep up with community-related feature iterations, such as popular plugins like ControlNet, and LoRa.

* **High Scalability**: This solution decouples the WebUI interface from the backend, allowing the WebUI to launch on supported terminals without GPU restrictions. Existing training, inference, and other tasks can be migrated to Amazon SageMaker through the provided extension functionalities, providing users with elastic computing resources, cost reduction, flexibility, and scalability.
















