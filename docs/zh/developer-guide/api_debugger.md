开启 API Debugger 功能步骤：

登陆安装有 WebUI 的 EC2，执行以下命令：

```bash
cd /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension
git pull
git checkout api_debugger
sudo systemctl restart sd-webui
```

等待重启 WebUI 完成，大约3分钟内。
