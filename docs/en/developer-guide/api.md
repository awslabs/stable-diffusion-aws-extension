---
title: Stable Diffusion AWS extension API v2023-07-05
language_tabs:
  - python: Python
  - javascript: Javascript
language_clients:
  - python: ""
  - javascript: ""
toc_footers: []
includes: []
headingLevel: 2

---

<!-- Generator: Widdershins v4.0.1 -->

<h1 id="stable-diffusion-train-and-deploy-api">Stable Diffusion AWS extension API</h1>

This document describe all the api for Stable Diffusion AWS extension solution.

**Base URLs:**

* <a href="https://\<Your API Gateway ID\>.execute-api.\<Your AWS Account Region\>.amazonaws.com/prod">https://\<Your API Gateway ID\>.execute-api.\<Your AWS Account Region\>.amazonaws.com/prod</a>

**Authentication**

* API Key (api_key)
    - Parameter Name: **x-api-key**, in: header. 

# API List table

| No. | API Name                                                                                                | Description |
| --- |---------------------------------------------------------------------------------------------------------| --- |
| 1 | [/inference/test-connection](#inferencetest-connection)                                                 | Test whether client can connect to api and check the API_TOKEN is correct |
| 2 | [/inference/list-inference-jobs](#inferencelist-inference-jobs)                                         | Lists all inference jobs. |
| 3 | [/inference/get-inference-job](#inferenceget-inference-job)                                             | Retrieves details of a specific inference job. |
| 4 | [/inference/get-inference-job-image-output](#inferenceget-inference-job-image-output)                   | Gets image output of a specific inference job. |
| 5 | [/inference/get-inference-job-param-output](#inferenceget-inference-job-param-output)                   | Gets parameter output of a specific inference job. |
| 6 | [/api/inference/run-sagemaker-inference](#apiinferencerun-sagemaker-inference)                          | Run sagemaker inference using default parameters|
| 7 | [/inference/deploy-sagemaker-endpoint](#inferencedeploy-sagemaker-endpoint)                             | Deploys a SageMaker endpoint. |
| 8 | [/inference/delete-sagemaker-endpoint](#inferencedelete-sagemaker-endpoint)                             | Deletes a SageMaker endpoint. |
| 9 | [/inference/list-endpoint-deployment-jobs](#inferencelist-endpoint-deployment-jobs)                     | Lists all endpoint deployment jobs. |
| 10 | [/inference/get-endpoint-deployment-job](#inferenceget-endpoint-deployment-job)                         | Gets a specific endpoint deployment job. |
| 11 | [/inference/generate-s3-presigned-url-for-uploading](#inferencegenerate-s3-presigned-url-for-uploading) | Generates an S3 presigned URL for uploading. |
| 12 | [/inference/get-texual-inversion-list](#inferenceget-texual-inversion-list)                             | Gets the list of textual inversions. |
| 13 | [/inference/get-lora-list](#inferenceget-lora-list)                                                     | Gets the list of LoRa. |
| 14 | [/inference/get-hypernetwork-list](#inferenceget-hypernetwork-list)                                     | Gets the list of hypernetworks. |
| 15 | [/inference/get-controlnet-model-list](#inferenceget-controlnet-model-list)                             | Gets the list of ControlNet models. |
| 16 | [/inference/run-model-merge](#inferencerun-model-merge)                                                 | Runs a model merge. |
| 17 | [/model(POST)](#modelpost)                                                                              | Creates a new model. |
| 18 | [/model(PUT)](#modelput)                                                                                | Upload the model file|
| 19 | [/models(GET)](#modelsget)                                                                              |Lists all models.|
| 20 | [/checkpoint(GET)](#checkpoint)                                                                         | Gets a checkpoint. |
| 21 | [/checkpoint(PUT)](#checkpointput)                                                                      | Updates a checkpoint. |
| 22 | [/checkpoints(GET)](#checkpoints)                                                                         | Lists all checkpoints. |
| 23 | [/train(POST)](#trainpost)                                                                              | Starts a training job. |
| 24 | [/train(PUT)](#trainput)                                                                                | Updates a training job. |
| 25 | [/trains(GET)](#trainsget)                                                                              | Lists all training jobs. |
| 26 | [/dataset(POST)](#datasetpost)                                                                          | Creates a new dataset. |
| 27 | [/dataset(PUT)](#datasetput)                                                                            | Updates a dataset. |
| 28 | [/datasets(GET)](#datasetsget)                                                                          | Lists all datasets. |
| 29 | [/{dataset_name}/data](#dataset_namedata)                                                               | Gets data of a specific dataset. |

<br/>

# /inference/test-connection
## test middleware connection

<a id="opIdtest_connection_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/test-connection', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/test-connection',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/test-connection`

> Example responses

> 200 Response

```json
null
```

<h3 id="used-to-let-client-test-connection-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="used-to-let-client-test-connection-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /api/inference/run-sagemaker-inference

<a id="opIdrun_sagemaker_inference_inference_run_sagemaker_inference_post"></a>

Generate a new image from a text prompt.

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  "Content-Type": "application/json",
  "Accept": "application/json",
  'x-api-key': 'API_TOKEN_VALUE'
}
body = {
  "stable_diffusion_model": ["v1-5-pruned-emaonly.safetensors"],
  "sagemaker_endpoint": "infer-endpoint-cb821ea",
  "task_type": "txt2img",
  "prompt": "a cute panda",
  "denoising_strength": 0.75
}

r = requests.post("https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/api/inference/run-sagemaker-inference", headers = headers, body = body)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "stable_diffusion_model": ["v1-5-pruned-emaonly.safetensors"],
  "sagemaker_endpoint": "infer-endpoint-cb821ea",
  "task_type": "txt2img",
  "prompt": "a cute panda",
  "denoising_strength": 0.75
}';
const headers = {
  "Content-Type":"application/json",
  "Accept":"application/json",
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch("https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/api/inference/run-sagemaker-inference",
{
  method: "POST",
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /api/inference/run-sagemaker-inference`

> Body parameter

```json
{
  "stable_diffusion_model": ["v1-5-pruned-emaonly.safetensors"],
  "sagemaker_endpoint": "infer-endpoint-cb821ea",
  "task_type": "txt2img",
  "prompt": "a cute panda",
  "denoising_strength": 0.75
}
```

<h3 id="run-sagemaker-inference-parameters">Parameters</h3>

> Parameter example

```json
{
  "sagemaker_endpoint": "infer-endpoint-ef3abcd", --- mandatory, endpoint name
  "task_type": "txt2img", --- mandatory, txt2img: text-to-image
  "prompt": "", --- mandatory, the prompt to generate an image
  "stable_diffusion_model": ["v1-5-pruned-emaonly.safetensors"], --- optional
  "embeddings": [], --- optional
  "lora_model": [], --- optional
  "hypernetwork_model": [], --- optional
  "controlnet_model": [], --- optional
  "denoising_strength": 0.75, --- optional
  "styles": [ 
    "string" --- optional
  ],
  "seed": -1, --- optional,
  "subseed": -1, --- optional
  "subseed_strength": 0, --- optional
  "seed_resize_from_h": -1, --- optional
  "seed_resize_from_w": -1, --- optional
  "batch_size": 1, --- optional, default is 1
  "n_iter": 1, --- optional, image number, default is 1
  "steps": 50, --- optional, default is 20
  "cfg_scale": 7, --- optional, default is 7 
  "width": 512, --- optional, default is 512
  "height": 512, --- optional, default is 512
  "restore_faces": false, --- optional
  "tiling": false, --- optional
  "negative_prompt": "string", --- optional, default is ""
  "override_settings": {}, --- hardcoded, parameter not work, it will be override in code, value is {}
  "script_args": [], --- optional
  "sampler_index": "Euler", --- optional, default is "Euler a"
  "script_name": "string", --- optional, default is ""
  "enable_hr": false, --- optional, enable hi-res
  "firstphase_width": 0, --- optional, default is 0
  "firstphase_height": 0,  --- optional, default is 0
  "hr_scale": 2, --- optional, default is 2
  "hr_upscaler": "string", --- optional, default is Latent
  "hr_second_pass_steps": 0, --- optional, default is 0
  "hr_resize_x": 0, --- optional
  "hr_resize_y": 0, --- optional
}
```
> Example responses

> 200 Response

```json
{
  "inference_id": "XXXXXXX",
  "status": "inprogress | failed",
  "endpoint_name": "NAME_OF_ENDPOINT",
  "output_path": "path_of_prediction_output"
}
```

<h3 id="run-sagemaker-inference-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<br/>

# /inference/deploy-sagemaker-endpoint

<a id="opIddeploy_sagemaker_endpoint_inference_deploy_sagemaker_endpoint_post"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.post('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/deploy-sagemaker-endpoint', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "instance_type": "ml.g4dn.xlarge | ml.g4dn.2xlarge | ml.g4dn.4xlarge",
  "initial_instance_count": "1|2|3|4"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/deploy-sagemaker-endpoint',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /inference/deploy-sagemaker-endpoint`

> Body parameter

```json
{
  "instance_type": "ml.g4dn.xlarge | ml.g4dn.2xlarge | ml.g4dn.4xlarge",
  "initial_instance_count": "1|2|3|4"
}
```

<h3 id="deploy-sagemaker-endpoint-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="deploy-sagemaker-endpoint-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="deploy-sagemaker-endpoint-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/delete-sagemaker-endpoint

<a id="opIddelete_sagemaker_endpoint_inference_delete_sagemaker_endpoint_post"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.post('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/delete-sagemaker-endpoint', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "delete_endpoint_list": [
    "infer-endpoint-XXXXXX",
    "infer-endpoint-YYYYYY"
  ]
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/delete-sagemaker-endpoint',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /inference/delete-sagemaker-endpoint`

> Body parameter

```json
{
  "delete_endpoint_list": [
    "infer-endpoint-XXXXXX",
    "infer-endpoint-YYYYYY"
  ]
}
```

<h3 id="delete-sagemaker-endpoint-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
null
```

<h3 id="delete-sagemaker-endpoint-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="delete-sagemaker-endpoint-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/list-endpoint-deployment-jobs

<a id="opIdlist_endpoint_deployment_jobs_inference_list_endpoint_deployment_jobs_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/list-endpoint-deployment-jobs', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/list-endpoint-deployment-jobs',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/list-endpoint-deployment-jobs`

> Example responses

> 200 Response

```json
[
  {
    "EndpointDeploymentJobId": "e0f9ccfd-8d14-4e77-9e75-b340e1ef23c8",
    "startTime": "2023-07-04 08:00:35.171309",
    "endTime": "2023-07-04 08:00:37.158519",
    "error": "",
    "status": "failed"
  },
  {
    "EndpointDeploymentJobId": "1bd447d2-e561-4cb3-965d-2707b30aea81",
    "startTime": "2023-07-04 08:00:22.435828",
    "endTime": "2023-07-04 08:00:25.421777",
    "error": "",
    "status": "failed"
  },
  {
    "EndpointDeploymentJobId": "cb821ea9-e9d1-4bae-98f8-c20ecadf11e0",
    "startTime": "2023-07-04 08:00:47.736033",
    "endTime": "2023-07-04 08:12:55.148070",
    "endpoint_name": "infer-endpoint-cb821ea",
    "endpoint_status": "InService",
    "status": "success"
  }
]
```

<h3 id="list-endpoint-deployment-jobs-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="list-endpoint-deployment-jobs-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/list-inference-jobs

<a id="opIdlist_inference_jobs_inference_list_inference_jobs_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/list-inference-jobs', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/list-inference-jobs',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/list-inference-jobs`

> Example responses

> 200 Response

```json
[
  {
    "inference_info_name": "/tmp/417d8bc5-f6d0-49c6-9669-c981beeb602a_param.json",
    "startTime": "2023-07-04 09:14:21.170303",
    "taskType": "txt2img",
    "completeTime": "2023-07-04-09-14-26",
    "InferenceJobId": "417d8bc5-f6d0-49c6-9669-c981beeb602a",
    "status": "succeed",
    "sagemakerRaw": "",
    "image_names": [
      "image_0.jpg"
    ]
  },
  {
    "inference_info_name": "/tmp/1f9679f3-25b8-4c44-8345-0a845da30094_param.json",
    "startTime": "2023-07-05 06:38:45.752740",
    "taskType": "txt2img",
    "completeTime": "2023-07-05-06-38-49",
    "InferenceJobId": "1f9679f3-25b8-4c44-8345-0a845da30094",
    "status": "succeed",
    "sagemakerRaw": "{'awsRegion': 'us-west-2', 'eventTime': '2023-07-05T06:38:47.73Z', 'receivedTime': '2023-07-05T06:38:45.725Z', 'invocationStatus': 'Completed', 'requestParameters': {'accept': '*/*', 'endpointName': 'infer-endpoint-cb821ea', 'inputLocation': 's3://sagemaker-us-west-2-489670441870/async-endpoint-inputs/infer-endpoint-cb821ea-230705-0638/2023-07-05-06-38-45-445-81a1ec03-f000-4a20-9a60-032ab1558a9d'}, 'responseParameters': {'contentType': 'application/json', 'outputLocation': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1tlr2pqwkosg3/sagemaker_output/211d2095-68bc-4404-a9e1-8a18a41f4dc7.out'}, 'inferenceId': '1f9679f3-25b8-4c44-8345-0a845da30094', 'eventVersion': '1.0', 'eventSource': 'aws:sagemaker', 'eventName': 'InferenceResult'}",
    "image_names": [
      "image_0.jpg"
    ]
  }
]
```

<h3 id="list-inference-jobs-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="list-inference-jobs-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/get-endpoint-deployment-job

<a id="opIdget_endpoint_deployment_job_inference_get_endpoint_deployment_job_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-endpoint-deployment-job', params={
  'jobID': 'string'
}, headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-endpoint-deployment-job?jobID=string',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/get-endpoint-deployment-job`

<h3 id="get-endpoint-deployment-job-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|jobID|query|string|true|none|

> Example responses

> 200 Response

```json
{
  "EndpointDeploymentJobId": "cb821ea9-e9d1-4bae-98f8-c20ecadf11e0",
  "startTime": "2023-07-04 08:00:47.736033",
  "endTime": "2023-07-04 08:12:55.148070",
  "endpoint_name": "infer-endpoint-cb821ea",
  "endpoint_status": "InService",
  "status": "success"
}
```

<h3 id="get-endpoint-deployment-job-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-endpoint-deployment-job-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/get-inference-job

<a id="opIdget_inference_job_inference_get_inference_job_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-inference-job', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-inference-job',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/get-inference-job`

<h3 id="get-inference-job-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|jobID|query|string|false|none|

> Example responses

> 200 Response

```json
{
  "inference_info_name": "/tmp/1f9679f3-25b8-4c44-8345-0a845da30094_param.json",
  "startTime": "2023-07-05 06:38:45.752740",
  "taskType": "txt2img",
  "completeTime": "2023-07-05-06-38-49",
  "InferenceJobId": "1f9679f3-25b8-4c44-8345-0a845da30094",
  "status": "succeed",
  "sagemakerRaw": "{'awsRegion': 'us-west-2', 'eventTime': '2023-07-05T06:38:47.73Z', 'receivedTime': '2023-07-05T06:38:45.725Z', 'invocationStatus': 'Completed', 'requestParameters': {'accept': '*/*', 'endpointName': 'infer-endpoint-cb821ea', 'inputLocation': 's3://sagemaker-us-west-2-489670441870/async-endpoint-inputs/infer-endpoint-cb821ea-230705-0638/2023-07-05-06-38-45-445-81a1ec03-f000-4a20-9a60-032ab1558a9d'}, 'responseParameters': {'contentType': 'application/json', 'outputLocation': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1tlr2pqwkosg3/sagemaker_output/211d2095-68bc-4404-a9e1-8a18a41f4dc7.out'}, 'inferenceId': '1f9679f3-25b8-4c44-8345-0a845da30094', 'eventVersion': '1.0', 'eventSource': 'aws:sagemaker', 'eventName': 'InferenceResult'}",
  "image_names": [
    "image_0.jpg"
  ]
}
```

<h3 id="get-inference-job-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-inference-job-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/get-inference-job-image-output

<a id="opIdget_inference_job_image_output_inference_get_inference_job_image_output_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-inference-job-image-output', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-inference-job-image-output',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/get-inference-job-image-output`

<h3 id="get-inference-job-image-output-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|jobID|query|string|false|none|

> Example responses

> 200 Response

```json
[
  "https://stable-diffusion-aws-extension-aigcbucketa457cb49-1tlr2pqwkosg3.s3.amazonaws.com/out/1f9679f3-25b8-4c44-8345-0a845da30094/result/image_0.jpg"
]
```

<h3 id="get-inference-job-image-output-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-inference-job-image-output-responseschema">Response Schema</h3>

Status Code **200**

*Response Get Inference Job Image Output Inference Get Inference Job Image Output Get*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|Response Get Inference Job Image Output Inference Get Inference Job Image Output Get|[string]|false|none|none|

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/get-inference-job-param-output

<a id="opIdget_inference_job_param_output_inference_get_inference_job_param_output_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-inference-job-param-output', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-inference-job-param-output',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/get-inference-job-param-output`

<h3 id="get-inference-job-param-output-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|jobID|query|string|false|none|

> Example responses

> 200 Response

```json
[
  "https://stable-diffusion-aws-extension-aigcbucketa457cb49-1tlr2pqwkosg3.s3.amazonaws.com/out/1f9679f3-25b8-4c44-8345-0a845da30094/result/1f9679f3-25b8-4c44-8345-0a845da30094_param.json"
]
```

<h3 id="get-inference-job-param-output-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<h3 id="get-inference-job-param-output-responseschema">Response Schema</h3>

Status Code **200**

*Response Get Inference Job Param Output Inference Get Inference Job Param Output Get*

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|Response Get Inference Job Param Output Inference Get Inference Job Param Output Get|[string]|false|none|none|

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/generate-s3-presigned-url-for-uploading

<a id="opIdgenerate_s3_presigned_url_for_uploading_inference_generate_s3_presigned_url_for_uploading_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/generate-s3-presigned-url-for-uploading', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/generate-s3-presigned-url-for-uploading',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/generate-s3-presigned-url-for-uploading`

<h3 id="generate-s3-presigned-url-for-uploading-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|s3_bucket_name|query|string|false|none|
|key|query|string|false|none|

> Example responses

> 200 Response

```json
"https://stable-diffusion-aws-extension-aigcbucketa457cb49-1tlr2pqwkosg3.s3.amazonaws.com/config/aigc.json?XXX"
```

<h3 id="generate-s3-presigned-url-for-uploading-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|string|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/get-texual-inversion-list

<a id="opIdget_texual_inversion_list_inference_get_texual_inversion_list_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-texual-inversion-list', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-texual-inversion-list',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/get-texual-inversion-list`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-textual-inversion-list-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-textual-inversion-list-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/get-lora-list

<a id="opIdget_lora_list_inference_get_lora_list_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-lora-list', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-lora-list',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/get-lora-list`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-lora-list-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-lora-list-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/get-hypernetwork-list

<a id="opIdget_hypernetwork_list_inference_get_hypernetwork_list_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-hypernetwork-list', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-hypernetwork-list',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/get-hypernetwork-list`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-hypernetwork-list-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-hypernetwork-list-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/get-controlnet-model-list

<a id="opIdget_controlnet_model_list_inference_get_controlnet_model_list_get"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-controlnet-model-list', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/get-controlnet-model-list',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /inference/get-controlnet-model-list`

> Example responses

> 200 Response

```json
null
```

<h3 id="get-controlnet-model-list-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="get-controlnet-model-list-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<br/>

# /inference/run-model-merge

<a id="opIdrun_model_merge_inference_run_model_merge_post"></a>

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.post('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/run-model-merge', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/run-model-merge',
{
  method: 'POST',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /inference/run-model-merge`

> Example responses

> 200 Response

```json
{
  "primary_model_name": "primary_model_name,",
  "secondary_model_name": "secondary_model_name,",
  "tertiary_model_name": "teritary_model_name"
}
```

<h3 id="run-model-merge-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|

<h3 id="run-model-merge-responseschema">Response Schema</h3>

<aside class="success">
This operation does not require authentication
</aside>

<h1 id="stable-diffusion-train-and-deploy-api-default">default</h1>

<br/>

# /model(POST)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.post('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/model', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "model_type": "Stable-diffusion",
  "name": "testmodelcreation01",
  "filenames": [
    {
      "filename": "v1-5-pruned-emaonly.safetensors.tar",
      "parts_number": 5
    }
  ],
  "params": {
    "create_model_params": {
      "new_model_name": "testmodelcreation01",
      "ckpt_path": "v1-5-pruned-emaonly.safetensors",
      "from_hub": false,
      "new_model_url": "",
      "new_model_token": "",
      "extract_ema": false,
      "train_unfrozen": false,
      "is_512": true
    }
  }
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/model',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /model`

> Body parameter

```json
{
  "model_type": "Stable-diffusion",
  "name": "testmodelcreation01",
  "filenames": [
    {
      "filename": "v1-5-pruned-emaonly.safetensors.tar",
      "parts_number": 5
    }
  ],
  "params": {
    "create_model_params": {
      "new_model_name": "testmodelcreation01",
      "ckpt_path": "v1-5-pruned-emaonly.safetensors",
      "from_hub": false,
      "new_model_url": "",
      "new_model_token": "",
      "extract_ema": false,
      "train_unfrozen": false,
      "is_512": true
    }
  }
}
```

<h3 id="create-model-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "job": {
    "id": "id",
    "status": "Initialed",
    "s3_base": "s3://S3_Location",
    "model_type": "Stable-diffusion",
    "params": {},
    "s3PresignUrl": [
      {
        "upload_id": "id",
        "bucket": "bucket name",
        "key": "object key"
      }
    ]
  }
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="create-model-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="create-model-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /model(PUT)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.put('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/model', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "model_id": "c9f59ee7-0672-4fd1-8a45-8a494de8a48d",
  "status": "Creating",
  "multi_parts_tags": {
    "v1-5-pruned-emaonly.safetensors.tar": [
      {
        "ETag": "cc95c41fa28463c8e9b88d67805f24e0",
        "PartNumber": 1
      },
      {
        "ETag": "e4378bd84b0497559c55be8373cb79d0",
        "PartNumber": 2
      },
      {
        "ETag": "815b68042f6ac5e60b9cff5c697ffea6",
        "PartNumber": 3
      },
      {
        "ETag": "2c6cfbd9bfbafd5664cdc8b3ba07df6d",
        "PartNumber": 4
      },
      {
        "ETag": "e613d37e5065b0cd63f1cad216423141",
        "PartNumber": 5
      }
    ]
  }
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/model',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /model`

> Body parameter

```json
{
  "model_id": "c9f59ee7-0672-4fd1-8a45-8a494de8a48d",
  "status": "Creating",
  "multi_parts_tags": {
    "v1-5-pruned-emaonly.safetensors.tar": [
      {
        "ETag": "cc95c41fa28463c8e9b88d67805f24e0",
        "PartNumber": 1
      },
      {
        "ETag": "e4378bd84b0497559c55be8373cb79d0",
        "PartNumber": 2
      },
      {
        "ETag": "815b68042f6ac5e60b9cff5c697ffea6",
        "PartNumber": 3
      },
      {
        "ETag": "2c6cfbd9bfbafd5664cdc8b3ba07df6d",
        "PartNumber": 4
      },
      {
        "ETag": "e613d37e5065b0cd63f1cad216423141",
        "PartNumber": 5
      }
    ]
  }
}
```

<h3 id="update-model-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "job": {
    "output_path": "s3://S3_Location",
    "id": "job.id",
    "endpointName": "endpoint_name",
    "jobStatus": "Created",
    "jobType": "Stable-diffusion"
  }
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="update-model-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="update-model-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /models(GET)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/models', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/models',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /models`

<h3 id="list-models-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|types|query|array[string]|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "models": {
    "id": "id",
    "model_name": "name",
    "created": 12341234,
    "params": {},
    "status": "Initialed",
    "output_s3_location": "s3://S3_LOCATION/"
  }
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="list-models-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="list-models-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /checkpoint

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.post('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/checkpoint', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "checkpoint_type": "Stable-diffusion",
  "filenames": [
    {
      "filename": "v1-5-pruned-emaonly.safetensors",
      "parts_number": 5
    }
  ],
  "params": {
    "new_model_name": "test_api",
    "number": 1,
    "string": "abc"
  }
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/checkpoint',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /checkpoint`

> Body parameter

```json
{
  "checkpoint_type": "Stable-diffusion",
  "filenames": [
    {
      "filename": "v1-5-pruned-emaonly.safetensors",
      "parts_number": 5
    }
  ],
  "params": {
    "new_model_name": "test_api",
    "number": 1,
    "string": "abc"
  }
}
```

<h3 id="create-checkpoint-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "checkpoint": {
    "id": "id",
    "type": "Stable-diffusion",
    "s3_location": "s3://S3_Location",
    "status": "Initialed",
    "params": {}
  },
  "s3PresignUrl": [
    {
      "upload_id": "id,",
      "bucket": "bucket name,",
      "key": "key,"
    }
  ]
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="create-checkpoint-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="create-checkpoint-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /checkpoint(put)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.put('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/checkpoint', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "checkpoint_id": "906a5a1f-6833-45aa-8a10-fb0e983e0eae",
  "status": "Active",
  "multi_parts_tags": {
    "v1-5-pruned-emaonly.safetensors.tar": [
      {
        "ETag": "cc95c41fa28463c8e9b88d67805f24e0",
        "PartNumber": 1
      },
      {
        "ETag": "e4378bd84b0497559c55be8373cb79d0",
        "PartNumber": 2
      },
      {
        "ETag": "815b68042f6ac5e60b9cff5c697ffea6",
        "PartNumber": 3
      },
      {
        "ETag": "2c6cfbd9bfbafd5664cdc8b3ba07df6d",
        "PartNumber": 4
      },
      {
        "ETag": "e613d37e5065b0cd63f1cad216423141",
        "PartNumber": 5
      }
    ]
  }
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/checkpoint',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /checkpoint`

> Body parameter

```json
{
  "checkpoint_id": "906a5a1f-6833-45aa-8a10-fb0e983e0eae",
  "status": "Active",
  "multi_parts_tags": {
    "v1-5-pruned-emaonly.safetensors.tar": [
      {
        "ETag": "cc95c41fa28463c8e9b88d67805f24e0",
        "PartNumber": 1
      },
      {
        "ETag": "e4378bd84b0497559c55be8373cb79d0",
        "PartNumber": 2
      },
      {
        "ETag": "815b68042f6ac5e60b9cff5c697ffea6",
        "PartNumber": 3
      },
      {
        "ETag": "2c6cfbd9bfbafd5664cdc8b3ba07df6d",
        "PartNumber": 4
      },
      {
        "ETag": "e613d37e5065b0cd63f1cad216423141",
        "PartNumber": 5
      }
    ]
  }
}
```

<h3 id="update-checkpoints-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "checkpoint": {
    "id": "id",
    "type": "Stable-diffusion",
    "s3_location": "s3://S3_Location",
    "status": "Active",
    "params": {}
  }
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="update-checkpoints-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="update-checkpoints-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /checkpoints

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/checkpoints', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/checkpoints',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /checkpoints`

<h3 id="list-checkpoints-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|status|query|array[string]|false|none|
|types|query|array[string]|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "checkpoints": [
    {
      "id": "id",
      "s3Location": "s3://S3_Location",
      "type": "Stable-diffusion",
      "status": "Active",
      "name": [
        "object_1",
        "object_2"
      ],
      "created": 12341234
    }
  ]
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="list-checkpoints-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="list-checkpoints-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /train(POST)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.post('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/train', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "train_type": "dreambooth",
  "model_id": "36c9d05e-3445-42a6-8be1-d7d054df7b9d",
  "params": {
    "train_params": {
      "training_instance_type": "ml.g4dn.2xlarge"
    },
    "test1": 2
  },
  "filenames": [
    "training_config.json",
    "images.tar"
  ]
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/train',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /train`

> Body parameter

```json
{
  "train_type": "dreambooth",
  "model_id": "36c9d05e-3445-42a6-8be1-d7d054df7b9d",
  "params": {
    "train_params": {
      "training_instance_type": "ml.g4dn.2xlarge"
    },
    "test1": 2
  },
  "filenames": [
    "training_config.json",
    "images.tar"
  ]
}
```

<h3 id="create-train-job-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "job": {
    "id": "id",
    "status": "Initialed",
    "trainType": "Stable-diffusion",
    "params": {},
    "input_location": "s3://S3_Location"
  },
  "s3PresignUrl": [
    {
      "filename": "s3://S3_Location"
    }
  ]
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="create-train-job-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="create-train-job-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /train(PUT)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.put('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/train', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "train_job_id": "b5183dd3-0279-46ff-b64e-6cd687c0fe71",
  "status": "Training"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/train',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /train`

> Body parameter

```json
{
  "train_job_id": "b5183dd3-0279-46ff-b64e-6cd687c0fe71",
  "status": "Training"
}
```

<h3 id="update-train-job-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "job": {
    "id": "id",
    "status": "Training",
    "created": 12341234,
    "trainType": "Stable-diffusion",
    "params": {},
    "input_location": "s3://S3_Location"
  }
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="update-train-job-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="update-train-job-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /trains(GET)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/trains', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/trains',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /trains`

<h3 id="list-train-jobs-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|types|query|array[string]|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": "200,",
  "trainJobs": [
    {
      "id": "id",
      "modelName": "model_name",
      "status": "Complete",
      "trainType": "Stable-diffusion",
      "created": 1234124,
      "sagemakerTrainName": "sagemaker_train_name"
    }
  ]
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="list-train-jobs-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="list-train-jobs-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /dataset(POST)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.post('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/dataset', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "dataset_name": "test_dataset",
  "content": [
    {
      "filename": "/path/to/a/file.png",
      "name": "another_name",
      "type": "png"
    }
  ],
  "params": {}
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/dataset',
{
  method: 'POST',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`POST /dataset`

> Body parameter

```json
{
  "dataset_name": "test_dataset",
  "content": [
    {
      "filename": "/path/to/a/file.png",
      "name": "another_name",
      "type": "png"
    }
  ],
  "params": {}
}
```

<h3 id="create-dataset-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "datasetName": "dataset_name",
  "s3PresignUrl": [
    {
      "filename": "s3://S3_Location"
    }
  ]
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="create-dataset-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="create-dataset-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /dataset(PUT)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.put('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/dataset', headers = headers)

print(r.json())

```

Javascript example code:

```javascript
const inputBody = '{
  "dataset_name": "test_dataset",
  "status": "Enabled"
}';
const headers = {
  'Content-Type':'application/json',
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/dataset',
{
  method: 'PUT',
  body: inputBody,
  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`PUT /dataset`

> Body parameter

```json
{
  "dataset_name": "test_dataset",
  "status": "Enabled"
}
```

<h3 id="update-dataset-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|body|body|object|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "datasetName": "dataset_name",
  "status": "Enabled"
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="update-dataset-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="update-dataset-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /datasets(GET)

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/datasets', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/prod/datasets',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /prod/datasets`

<h3 id="list-datasets-by-dataset-status-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|dataset_status|query|array[string]|false|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "datasets": [
    {
      "datasetName": "dataset_name",
      "s3": "s3://S3_Location",
      "status": "Enabled",
      "timestamp": 1234124
    }
  ]
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="list-datasets-by-dataset-status-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="list-datasets-by-dataset-status-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

<br/>

# /{dataset_name}/data

### **Code samples :**

Python example code:

```Python
import requests
headers = {
  'Accept': 'application/json',
  'x-api-key': 'API_TOKEN_VALUE'
}

r = requests.get('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/{dataset_name}/data', headers = headers)

print(r.json())

```

Javascript example code:

```javascript

const headers = {
  'Accept':'application/json',
  'x-api-key':'API_TOKEN_VALUE'
};

fetch('https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/{dataset_name}/data',
{
  method: 'GET',

  headers: headers
})
.then(function(res) {
    return res.json();
}).then(function(body) {
    console.log(body);
});

```

`GET /{dataset_name}/data`

<h3 id="list-dataset-items-by-dataset-name-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|dataset_name|path|string|true|none|

> Example responses

> 200 Response

```json
{
  "statusCode": 200,
  "dataset_name": "dataset_name",
  "data": [
    {
      "key": "key",
      "name": "file name",
      "type": "image",
      "preview_url": "https://presigned_s3_url",
      "dataStatus": "Enabled"
    }
  ]
}
```

> 500 Response

```json
{
  "statusCode": 500,
  "error": "error_message"
}
```

<h3 id="list-dataset-items-by-dataset-name-responses">Responses</h3>

|Status|Meaning|Description|Schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful response|Inline|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|Error response|Inline|

<h3 id="list-dataset-items-by-dataset-name-responseschema">Response Schema</h3>

<aside class="warning">
To perform this operation, you must be authenticated by means of one of the following methods:
api_key
</aside>

# Schemas

<h2 id="tocS_Empty">Empty</h2>
<!-- backwards compatibility -->
<a id="schemaempty"></a>
<a id="schema_Empty"></a>
<a id="tocSempty"></a>
<a id="tocsempty"></a>

```json
{}

```

Empty Schema

### Properties

*None*

<h2 id="tocS_HTTPValidationError">HTTPValidationError</h2>
<!-- backwards compatibility -->
<a id="schemahttpvalidationerror"></a>
<a id="schema_HTTPValidationError"></a>
<a id="tocShttpvalidationerror"></a>
<a id="tocshttpvalidationerror"></a>

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}

```

HTTPValidationError

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|detail|[[ValidationError](#schemavalidationerror)]|false|none|none|

<h2 id="tocS_ValidationError">ValidationError</h2>
<!-- backwards compatibility -->
<a id="schemavalidationerror"></a>
<a id="schema_ValidationError"></a>
<a id="tocSvalidationerror"></a>
<a id="tocsvalidationerror"></a>

```json
{
  "loc": [
    "string"
  ],
  "msg": "string",
  "type": "string"
}

```

ValidationError

### Properties

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|loc|[anyOf]|true|none|none|

anyOf

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|string|false|none|none|

or

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|» *anonymous*|integer|false|none|none|

continued

|Name|Type|Required|Restrictions|Description|
|---|---|---|---|---|
|msg|string|true|none|none|
|type|string|true|none|none|

