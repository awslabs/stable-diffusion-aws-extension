# Main Tab
This chapter will provide a detailed overview of the convenient cloud-based resource management approach offered by this solution.

## Upload Model
To use extra models for inference, you will need to upload model through steps below, and follow steps in [txt2img](txt2img-guide.md) or [img2img](img2img-guide.md)to inference with extra models as need.

1. Within Stable Diffusion WebUI, navigate to solution main tab **Amazon SageMaker**, find session **Cloud Assets Management**.
![Upload Models to S3](../images/Upload-models.png)
2. Enter the local model path under correspoding model text box. 
> **Note**: You can upload multiple kinds of models by entering multiple local model paths in text box.

3. Click **Upload Models to Cloud** to start uploading process.
4. Message will appear on left right once uploading completes.



## Amazon SageMaker Endpoint Management
### Deploy new endpoint
1. Within Stable Diffusion WebUI, navigate to solution main tab **Amazon SageMaker**, find session **Cloud Assets Management**, **Deploy New SageMaker Endpoint**, select Amazon SageMaker instance type for inference under **SageMaker Instance Type**, and count in **Please select Instance count**, click **Deploy**, message *Endpoint deployment started* will appear on the left side.
2. You can navigate to tab **txt2img**, session **Amazon SageMaker Inference**, refresh and select drop down list **Select Cloud SageMaker Endpoint** to check all the deployment status of endpoints.
    > **Note:** The format of the drop down list is：endpoint name+ deployment status (including Creating/Failed/InService)+deployment completing time。
3. It will take around 10 mins for endpoint deployment status changing to *InService*, which indicates that the endpoint has been successfully deployed.


### Delete deployed endpoints
1. Refresh and select endpoint(s) under dropdown list of **Select Cloud SageMaker Endpoint**.
2. Click **Delete**, message *Endpoint delete completed* will appear on left side, which indicates that the selected endpoint(s) havs been successfully deleted.



