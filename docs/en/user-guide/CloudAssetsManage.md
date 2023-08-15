# Main Tab
This chapter will provide a detailed overview of the convenient cloud-based resource management approach offered by this solution.

## Upload Model
To use extra models for inference, you could upload model through steps below in two ways, and follow steps in [txt2img](txt2img-guide.md) or [img2img](img2img-guide.md)to inference with extra models as need.

### Upload model from webUI to cloud
Considering the diverse range of user scenarios, this approach is suitable for deploying the webUI frontend on machines other than the local computer. Similar to the native using process of webUI, user is expected to put corresponding models under correct type of sub-foloder of webUI project. And user can follow the steps below for uploading such models to cloud for further processing. 

1. Navigate to solution main tab **Amazon SageMaker**, find session **Cloud Assets Management**, **Upload Model to S3 from WebUI**.
![Upload Models to S3](../images/Upload-models-old.png)
2. Select the corresponding model path that is expected to be uploaded, and click **Upload Models to Cloud** to start uploading process..
> **Note**: You can upload multiple kinds of models by entering multiple local model paths in text box.
3. Message will display on left right once uploading completes.

### Upload model from local to cloud
Considering the diverse range of user scenarios, this approach is suitable for deploying the webUI frontend on the local computer.

1. Navigate to solution main tab **Amazon SageMaker**, find session **Cloud Assets Management**, **Upload Model to S3 from local**.
![Upload Models to S3](../images/Upload-models-new.png)
2. Select the type of the model from drop down list, and select file(s) that are expected to upload by clicking **Browser**. Currently the module supports six types of model uploading, which are SD Checkpoints, Textual Inversion, LoRA model, ControlNet model, Hypernetwork, VAE.
> **Note**: You can select models multiple, but subject to browser restrictions, it is best to select no more than 10 files, and the total size should not exceed 8g.

3. Click **Upload Models to Cloud** to start uploading process.
4. The upload will be uploaded in pieces asynchronously based on the file size and quantity. After each piece is uploaded, you will see a prompt under the **Choose File** button


## Amazon SageMaker Endpoint Management
### Deploy new endpoint
1. Navigate to solution main tab **Amazon SageMaker**, find session **Cloud Assets Management**, **Deploy New SageMaker Endpoint**.
2. To simplify the user deployment process, this solution defaults the endpoint configuration to an ml.g5.2xlarge instance type, 1 instance count with auto scale enabled. If users have additional requirements, they can check the **Advanced Endpoint Configuration** . Below the checkbox, more selectable parameters will be displayed, including options for custom endpoint naming, instance types, and instance counts. Additionally, users can indicate whether the new endpoint deployment requires auto scale by checking the **Enable Autoscaling** option. Once all parameter selections are complete, click **Deploy** to proceed.
select Amazon SageMaker instance type for inference under **SageMaker Instance Type**, and count in **Please select Instance count**, click **Deploy**, message *Endpoint deployment started* will appear on the left side.
3. You can navigate to tab **txt2img**, session **Amazon SageMaker Inference**, refresh and select drop down list **Select Cloud SageMaker Endpoint** to check all the deployment status of endpoints.

    > **Note:** The format of the drop down list is：endpoint name+ deployment status (including Creating/Failed/InService)+deployment completing time.

4. It will take around 10 mins for endpoint deployment status changing to *InService*, which indicates that the endpoint has been successfully deployed.

### Delete deployed endpoints
1. Refresh and select endpoint(s) under dropdown list of **Select Cloud SageMaker Endpoint**.
2. Click **Delete**, message *Endpoint delete completed* will appear on left side, which indicates that the selected endpoint(s) havs been successfully deleted.



## AWS Dataset Management

### Create Dataset
In functions such as model fine-tuning, it is necessary to provide a file of images for fine-tuning work. This functional module helps users quickly upload images to the cloud.

1. Navigate to main tab **Amazon SageMaker**, section **AWS Dataset Management**，sub-tab **Create**.
![Create Dataset to S3](../images/Dataset-management.png)

2. Click **Click to Upload a File**, in the local file browser that pops up, confirm to select all the images required for one model fine-tuning.
3. Enter file name in **Dataset Name**, enter file description in **Dataset Description**, click **Create Dataset**.
4. The meessage **Complete Dataset XXXX creation** will be displayed once process completes.

### Explore Dataset
Once the dataset upload is completed, this feature module allows users to quickly explore and obtain the corresponding S3 address for the dataset. Users can copy this S3 path and paste it into the appropriate location where image collections need to be uploaded.

1. Navigate to **Amazon SageMaker** tab，**AWS Dataset Management** - **Browse** session.
2. Refresh the drop down list of **Dataset From Cloud**, and select target dataset name.
3. Field **dataset s3 location** will display corresponding S3 address, user can copy as need.
