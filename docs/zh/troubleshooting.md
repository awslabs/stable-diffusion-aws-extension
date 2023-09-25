以下内容将帮助您在使用 Stable Diffusion亚马逊云科技插件解决方案时遇到错误或问题时进行修复。

 **错误: 在我推理图片时遇到错误'RuntimeError: "LayerNormKernelImpl" not implemented for 'Half''**

当您于CPU机型上启动webUI前端时，可能会遇到这样的问题。建议在启动webUI时加入 `--precision full --no-half`
```
./webui.sh --skip-torch-cuda-test --precision full --no-half
```


**错误: 我在启动webUI时，遇到venv安装失败的信息 `python3 -m venv env`** 

当您的系统默认使用Python 3.9，而Ubuntu 20.04使用的是Python 3.8时，会出现此错误。用户可以使用`sudo apt install python3.8-venv`安装venv包，以显式地指定Python的完整版本。


