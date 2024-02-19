Steps to enable API Debugger function:
Login to EC2 with WebUI installed and execute the following command:

```Bash
cd /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension
git pull
git checkout api_debugger
sudo systemctl restart sd-webui
```
Wait for the WebUI to restart and complete within approximately 3 minutes.
