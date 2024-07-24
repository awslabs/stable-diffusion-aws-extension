# Image or Video generation through ComfyUI in the cloud

After successfully deploying the solution, you can open the native **ComfyUI** page provided by the deployed stack. The summary steps for workflow debugging, releasing, and inference are as follows:

* Step 1: Connect to the EC2 that deploys ComfyUI frontend.
* Step 2: Open the **Designer** link provided by the stack of solution, debug the new workflow locally (on the EC2 virtual machine), install the missing nodes, upload the required inference models, and ensure they can be successfully loaded and inferred locally (on the EC2 virtual machine).
* Step 3: Repeat Step 2 as needed to **publish multiple workflow templates**.
* Step 4: After debugging one (or more) workflow templates, package and **publish the current environment** with one click, and deploy a new Amazon SageMaker inference endpoint.
* Step 5: On the ComfyUI inference page, select the published templates and, if needed, modify the inference prompts, inference models, and inference images/videos. This step will use Amazon SageMaker resources.


## Step 1: Connect to the EC2 that deploys ComfyUI frontend

By connecting to the EC2 instance, you can check the corresponding directory structure locally, making it easier to view the log files during local workflow debugging and aid in diagnostics.

If you only need to view the local ComfyUI debugging logs, you can also achieve this through the following steps:

1. Open the EC2 console in the same region where the deployment solution is located, select the **comfy-on-aws-dev** instance, and click **Connect** in the top right corner.
2. In the available connection methods, select the **EC2 Instance Connect** tab and click **Connect**.
3. After a short wait, a new EC2 connection page will pop up. You can enter the required commands as needed to perform various operations. Common commands include:

```
tail -f /var/log/cloud-init-output.log     Used for real-time viewing of the initial logs during the EC2 startup process for Comfy.
sudo journalctl -u comfy -f       Used for real-time viewing of Comfy runtime logs.
tail -f /root/stable-diffusion-aws-extension/container/*.log       Used to view all logs of the Comfy runtime container.
sudo journalctl -u comfy --no-pager -n 200        Used to view the last 200 logs of the Comfy runtime.
docker images -q | xargs docker rmi -f
```

## Step 2: Debug the workflow
In the native **Designer** page provided by this solution, you can debug new workflows using the same methods as the local version of ComfyUI. Model management, and other tasks can be performed by connecting to the virtual machine (EC2) where ComfyUI is deployed.

![major-designer](../../images/senior-design.png)

The steps for using the senior design version of ComfyUI are summarized as follows:

1. (Optional) Drag an existing workflow JSON file into the ComfyUI interface to render the workflow.
2. Adjust (including adding and deleting) work nodes (custom nodes), and adjust inference parameters and the models used.
3. Click **Queue Prompt** to start an inference task based on the current page workflow.
4. (Optional) If step 3 results in an error prompt, follow the instructions to resolve it. For example, if a missing model is indicated, download the model to the corresponding directory on the EC2 instance; if missing custom nodes are indicated, click **Manager** and then **Install Missing Custom Nodes** to install the missing nodes. After resolving the error, repeat step 3 to test again.
![ComfyUI Management](../../images/ComfyUI-Manager.png)

5. Once the workflow is complete and the generated results are displayed on the interface, it indicates that the workflow debugging has been successful.
6. Click the plus sign above the **Template List** module in the right navigation bar. In the pop-up window, enter the name of the template to be published and the runtime environment to be bound, then click **OK**. 

    !!! tip
        Please note that the new template name must not exceed 20 characters in length, should be a combination of letters and numbers, and is case-sensitive. Additionally, the name must be unique within the same region; if it conflicts with an existing template name, a creation error will be prompted. If the runtime environment is not yet published, you can return to modify the published templates after completing Step 4 to bind the correct runtime environment.
![template release](../../images/template_release.png)

7. During the workflow publishing process, no updates should be made on the ComfyUI frontend. This process generally takes about ten seconds. After the publication is complete, a pop-up message will appear on the frontend indicating that the publication is finished.
8. Once the publishing is complete, refresh the page to see the newly published template in the workflow template list on the right navigation bar.

## Step 3: Repeat Step 2 as needed to publish multiple templates
To ensure workflow stability and compatibility, and to maximize resource utilization, it is recommended that users continuously debug and publish multiple workflow templates within the ComfyUI default environment. Once these workflows are ready, the combined running environment should be published and bound to an Amazon SageMaker Inference Endpoint. This setup allows the published environment to stably run multiple templates while maximizing the resource utilization of the inference endpoint. Additionally, consider the environment size when publishing; a larger environment may result in longer cold start times during subsequent auto-scaling. Balancing the number of templates bound to a single environment is a trade-off decision users need to make.

## Step 4: Deploy new inference endpoint for future inference of released template
After completing Step 3, users can package and publish the workflow runtime environment with one click and create an Amazon SageMaker Inference Endpoint for cloud-based inference based on the selected workflow template.

1. Click **New Environment** in the right navigation bar.
2. In the pop-up dialog, enter the name for the environment to be published. In the *Endpoint Config* section, select the parameters for the Amazon SageMaker Inference Endpoint to be bound to this environment, including instance type, auto-scaling options, etc. Click **OK** when finished.
3. The environment publishing process may take an uncertain amount of time, potentially up to 10+ minutes, depending on the size of the existing environment. During this time, the page will be locked to prevent any other operations that might disrupt the environment and cause the publishing process to fail.
4. Once the creation is successful, refresh the page. In the **Template List** section, select the templates to be bound, click the pencil icon, choose the newly published environment in the pop-up dialog, and click **OK**.

## Step 5: Inference of released template
In the view of **Designer** or **Junior Artists**, you can easily perform inference based on a template using the following steps:

1. Open the ComfyUI page and select a released template from the right-hand navigation bar. If in **Designer** view, also need to select the **Prompt on AWS** checkbox in the right-hand navigation bar.
2. The selected template will be automatically render in the ComfyUI page. Adjust the parameters as needed, and click **Queue Prompt** to submit the inference task.
3. Once the inference task is completed, the generated results will automatically be displayed on the page.


## Manage model(s)
### Upload model
To ensure smooth access during the model debugging phase, new models need to be uploaded to EC2. You can achieve this by entering the corresponding subfolder for the model category under the **models** directory on EC2. Use either direct drag-and-drop or the **wget** command with the model download URL. Considering network speed, it is recommended to prioritize using the **wget** method for model downloads.

