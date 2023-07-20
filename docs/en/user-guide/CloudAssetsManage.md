# Main Tab
This chapter will provide a detailed overview of the convenient cloud-based resource management approach offered by this solution.

## Upload Model
To use extra models for inference, you will need to upload model through steps below, and follow steps in [txt2img](txt2img-guide.md) or [img2img](img2img-guide.md)to inference with extra models as need.

1. Within Stable Diffusion WebUI, navigate to solution main tab **Amazon SageMaker**, find session **Cloud Assets Management**.
![Upload Models to S3](../images/Upload-models.png)
2. Enter the local model path under corresponding model text box. 
> **Note**: You can upload multiple kinds of models by entering multiple local model paths in text box.

3. Click **Upload Models to Cloud** to start uploading process.
4. Message will appear on left right once uploading completes.



## Amazon SageMaker Endpoint Management
### Deploy new endpoint
1. Within Stable Diffusion WebUI, navigate to solution main tab **Amazon SageMaker**, find session **Cloud Assets Management**, **Deploy New SageMaker Endpoint**, select Amazon SageMaker instance type for inference under **SageMaker Instance Type**, and count in **Please select Instance count**, click **Deploy**, message *Endpoint deployment started* will appear on the left side.
![Deploy new endpoint](../images/Deploy-new-endpoint.png)
2. You can navigate to tab **txt2img**, session **Amazon SageMaker Inference**, refresh and select drop down list **Select Cloud SageMaker Endpoint** to check all the deployment status of endpoints.

    > **Note:** The format of the drop down list is：endpoint name+ deployment status (including Creating/Failed/InService)+deployment completing time.

3. It will take around 10 mins for endpoint deployment status changing to *InService*, which indicates that the endpoint has been successfully deployed.


### Delete deployed endpoints
1. Refresh and select endpoint(s) under dropdown list of **Select Cloud SageMaker Endpoint**.
2. Click **Delete**, message *Endpoint delete completed* will appear on left side, which indicates that the selected endpoint(s) havs been successfully deleted.



# AWS Dataset Management

## Create Dataset
In functions such as model fine-tuning, it is necessary to provide a file of images for fine-tuning work. This functional module helps users quickly upload images to the cloud.

1. Navigate to main tab **Amazon SageMaker**, section **AWS Dataset Management**，sub-tab **Create**.
![Create Dataset to S3](../images/Dataset-management.png)

2. Click **Click to Upload a File**, in the local file browser that pops up, confirm to select all the images required for one model fine-tuning.
3. Enter file name in **Dataset Name**, enter file description in **Dataset Description**, click **Create Dataset**.
4. Once the message **Complete Dataset XXXX creation**，即表示该数据集已经成功上传到云上。

## 数据集浏览
数据集上传完成后，通过此功能模块，能够帮助用户快速得到数据集对应的云上地址。用户可以复制此地址，粘贴到对应需要上传图片集的地址位置。

1. 进入解决方案主标签页**Amazon SageMaker**，**AWS Dataset Management**区块，**Browse**标签页。
2. 刷新**Dataset From Cloud**列表，选择需要浏览的图片集名称。
3. 等待几秒，**dataset s3 location**区域即会显示该数据集的云上S3地址，复制粘贴即可取用，做后续步骤。

