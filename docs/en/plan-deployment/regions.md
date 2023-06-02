As of June 2023, this solution is supported in the following Amazon Web Services Regions:

- us-east-1 (Virginia)
- us-east-2 (Ohio)  
- us-west-1 (N. California)
- us-west-2 (Oregon)  
- ca-central-1 (Canada) 
- sa-east-1 (Sao Paulo)
- eu-west-1 (Ireland)
- eu-west-2 (London)
- eu-west-3 (Paris)   
- eu-central-1 (Frankfurt)  
- eu-north-1 (Stockholm)
- ap-northeast-1 (Tokyo) 
- ap-northeast-2 (Seoul)  
- ap-northeast-3 (Osaka)
- ap-southeast-1 (Singapore)  
- ap-southeast-2 (Sydney)   
- ap-south-1 (Mumbai)  
- ap-east-1 (Hong Kong)


!!!Important "Notice"
    Recently, it's observed that newly created Amazon S3 bucket, in us-east-2, us-west-1, us-west-2, there is an issue with CORS that prevents users from uploading configuration files through the browser. Despite updating the CORS configuration, users frequently encounter CORS issues when uploading files using pre-signed URLs. The problem resolves itself after approximately two hours. We are currently in communication with the Amazon S3 Service team regarding this issue. According to that, it's recommended to deploy the solution in us-east-1, ap-northeast-1 or ap-southeast-1.