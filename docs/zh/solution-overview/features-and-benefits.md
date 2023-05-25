## 主要功能

本解决方案支持以下Stable Diffusion WebUI的原生功能/第三方插件的云上工作：


| **功能**  | **支持版本** |
| ------------- | ------------- |
| [txt2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui)  | Content Cell  |
| [img2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui)  | Content Cell  |
| [ControlNet](https://github.com/Mikubill/sd-webui-controlnet)  | V1.1.189  |
| [Dreambooth](https://github.com/d8ahazard/sd_dreambooth_extension)  | Content Cell  |
| [Image browser](https://github.com/yfszzx/stable-diffusion-webui-images-browser)  | Content Cell  |



## 产品优势

* **安装便捷**。本解决方案使用CloudFormation一键部署AWS中间件，搭配社区原生Stable Diffusion WebUI插件安装形式一键安装，即可赋能用户快速使用Amazon SageMaker云上资源，进行推理和训练工作。
* **社区原生**。WebUI界面与后端分离，用户无需改变现有Stable Diffusion WebUI的使用习惯，WebUI可以在任何支持的终端启动而没有GPU的限制，原有训练，推理等任务通过插件所提供的功能迁移到Amazon SageMaker。
* **可扩展性强**。方案插件以及中间件代码开源，采取非侵入式设计，有助于用户快速跟上社区相关功能的迭代，从WebUI本体到广受欢迎的Dreambooth、ControlNet等插件。
* **优化资源配置**。用户可按需选择云上资源，进行批量推理及模型训练，极大提升效率。
* **协作性强**。依托于开源社区强大资源，通过插件形式可以与其他开发者合作，有助于更快速迭代产品，为用户提供更有用、易用的产品。