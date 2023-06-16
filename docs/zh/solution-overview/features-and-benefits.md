## 主要功能

本解决方案支持以下Stable Diffusion WebUI的原生功能/第三方插件的云上工作：


| **功能**  | **支持版本** |  **注释** |
| ------------- | ------------- | ------------- |
| [txt2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui)  | V1.2.1  | |
| [LoRa](https://github.com/AUTOMATIC1111/stable-diffusion-webui)  | V1.2.1  | |
| [ControlNet](https://github.com/Mikubill/sd-webui-controlnet)  | V1.1.189  | Not support preprocessor 'inpaint_global_harmonious'|
| [Dreambooth](https://github.com/d8ahazard/sd_dreambooth_extension)  | 20230331  | |
| [Image browser](https://github.com/yfszzx/stable-diffusion-webui-images-browser)  | Latest  | |
| img2img | 2023年6月底推出 | |



## 产品优势

* **安装便捷**。本解决方案使用CloudFormation一键部署AWS中间件，搭配社区原生Stable Diffusion WebUI插件安装形式一键安装，即可赋能用户快速使用Amazon SageMaker云上资源，进行推理、训练和调优工作。
* **社区原生**。该方案以插件形式实现，用户无需改变现有Web用户界面的使用习惯。此外，该方案的代码是开源的，采用非侵入式设计，有助于用户快速跟上社区相关功能的迭代，例如备受欢迎的Dreambooth、ControlNet和LoRa等插件。
* **可扩展性强**。本解决方案将WebUI界面与后端分离，WebUI可以在支持的终端启动而没有GPU的限制；原有训练，推理等任务通过插件所提供的功能迁移到Amazon SageMaker，为用户提供弹性计算资源、降低成本、提高灵活性和可扩展性。
