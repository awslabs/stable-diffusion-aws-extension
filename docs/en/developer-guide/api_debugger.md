## Enable Debugger

> Note: This feature will be enabled by default after `1.4.1`

Login to EC2 with WebUI installed and execute the following command:

```Bash
cd /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension
git pull
git checkout api_debugger
sudo systemctl restart sd-webui
```
Wait for the WebUI to restart and complete within approximately 3 minutes.

## Use API Debugger

After completing an inference job, open the API request record in the following order:

1. Click the button to refresh the inference history job list
2. Pull down the inference job list, find and select the job
3. Click the `API` button on the right

![debugger](../images/api_debugger.png)

## API Debugger Log

![debugger_log](../images/api_debugger_log.png)
