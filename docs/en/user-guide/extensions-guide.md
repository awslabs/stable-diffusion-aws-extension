# Other Extensions User Guide

## Extension ReActor for FaceSwap 

You can open the **ReActor** tab session, combining native windows of **txt2img** or **img2img** with solution tab **Amazon SageMaker Inference**, to achieve faceswap feature on cloud.

### User Guide
Here is an example of using ReActor in **txt2img** to introduce the recommended steps.
1. Select a base model under **Stable Diffusion Checkpoint Used on Cloud**, the *Generate* button will automatically change to "generate on cloud".
2. Assuming you want to generate an image of a girl with the appearance of the Mona Lisa, fill in the prompt box with "a girl".
3. Open tab of **ReActor**, drag image of Mona Lisa into *Single Source Image*.
![Setting-Reactor](../images/reactor.png)
4. Click *Generate on cloud*, and result will be presented in **Output** session as below.
![Setting-Reactor](../images/reactor_result.png)

Reactor supports multi-face swapping simultaneously by specifying the index of the face. It also allows loading face models for swapping. For more detailed usage instructions, please refer to the [extension documentation](https://github.com/Gourieff/sd-webui-reactor){:target="_blank"}


## Extension Tiled Diffusion & Tiled VAE for Image Super Resolution

You can use tab of **Tiled VAE**, combining with native **txt2img** or **img2img** with solution tab **Amazon SageMaker Inference**, in order to achieve image super resolution work. 


### User Guide
By utilizing these two extensions, it is able to generate ultra-high-resolution images within limited VRAM. Here, we'll take the example of using these extensions in **txt2img** to demonstrate how to perform super-resolution inference:

1. Select a base model under **Stable Diffusion Checkpoint Used on Cloud**, the *Generate* button will automatically change to "generate on cloud".
2. Assuming you want to generate an image of a cat, fill in the prompt box with "a cat".
3. Open Tiled Diffusion **Hires.fix**, and set the upscaling factor to 4x for super-resolution.
![Setting-tiledvae](../images/tiledvae1.png)
4. Open **Tiled VAE**，Enable Tiled VAE, you can generate the image using the default parameters.
![Setting-tiledvae](../images/tiledvae2.png)
5. Click *Generate on cloud*, and result will be presented in **Output** session.
![Setting-tiledvae](../images/tiledvae_result.png)

Tiled Diffusion supports setting different prompts for different regions to generate ultra-high-resolution images. For detailed usage instructions, please refer to the [extension documentation](https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111/tree/main){:target="_blank"}
