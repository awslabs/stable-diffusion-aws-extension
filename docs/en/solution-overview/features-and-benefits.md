## Features

This solution supports the cloud-based operations of the following native features/third-party extensions of Stable Diffusion WebUI:

| **Feature**  | **Supported Version** | **Note** |
| ------------- | ------------- | ------------- |
| [txt2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui)  | V1.2.1  | |
| [LoRa](https://github.com/AUTOMATIC1111/stable-diffusion-webui)  | V1.2.1  | |
| [ControlNet](https://github.com/Mikubill/sd-webui-controlnet)  | V1.1.189  | Not support preprocessor 'inpaint_global_harmonious'|
| [Dreambooth](https://github.com/d8ahazard/sd_dreambooth_extension)  | 20230331  | |
| [Image browser](https://github.com/yfszzx/stable-diffusion-webui-images-browser)  | Latest  | |
| img2img | Coming by end of June 2023 | |


## Benefits
* **Convenient Installation**: This solution leverages CloudFormation for easy deployment of AWS middleware. Combined with the installation of the native Stable Diffusion WebUI features and third-party extensions, users can quickly utilize Amazon SageMaker's cloud resources for inference, training and finetuning tasks.

* **Native Integration**: The WebUI interface is decoupled from the backend, allowing users to retain their existing usage habits with Stable Diffusion WebUI. The WebUI can be launched on any supported terminal without GPU limitations. Existing inference, training and finetuning tasks can be migrated to Amazon SageMaker using the functionality provided by the solution.

* **Strong Scalability**: The solution's extension and middleware code are open source and designed with a non-intrusive approach. This facilitates rapid adoption of community-related features, ranging from the core WebUI to popular thrid-party extensions like Dreambooth and ControlNet.

* **Optimized Resource Configuration**: Users can choose cloud resources based on their needs for batch inference and model training, significantly enhancing efficiency.

* **Strong Collaboration**: With the support of the open-source community, collaboration with other developers is facilitated through the extension framework. This helps accelerate product iteration, providing users with more useful and user-friendly products.
















