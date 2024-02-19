# 1.4.0

# 健康检查（Ping）

<a id="opIdTestConnection"></a>

## GET 健康检查 （Ping）

GET /ping

测试客户端是否可以连接到 API，并检查配置是否正确。
Test whether client can connect to api and check the API_TOKEN is correct.

> Response Examples

> Success

```json
{
  "message": "pong",
  "statusCode": 200
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

HTTP Status Code **200**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» message|string|true|none||none|
|» statusCode|integer|true|none||none|

# 角色（Roles）

<a id="opIdListRoles"></a>

## DELETE 删除角色 DeleteRoles

DELETE /roles

删除角色
Delete roles

> Body Parameters

```json
{
  "role_name_list": [
    "role_name_1"
  ]
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|
|body|body|object| no |none|
|» role_name_list|body|[string]| yes |角色列表（Role Name List）|

> Response Examples

> 204 Response

```json
{}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|204|[No Content](https://tools.ietf.org/html/rfc7231#section-6.3.5)|No Content|Inline|

### Responses Data Schema

<a id="opIdCreateRole"></a>

## POST 创建角色 CreateRole

POST /roles

创建新角色
Create a new role

> Body Parameters

```json
{
  "role_name": "new_role_name",
  "creator": "admin",
  "permissions": [
    "train:all",
    "checkpoint:all"
  ]
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|
|body|body|[Role](#schemarole)| no |none|

> Response Examples

> Created

```json
{
  "statusCode": 201,
  "message": "role created"
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|201|[Created](https://tools.ietf.org/html/rfc7231#section-6.3.2)|Created|Inline|

### Responses Data Schema

HTTP Status Code **201**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» message|string|true|none||none|

# 用户（Users）

<a id="opIdListUsers"></a>

## GET 获取用户列表 ListUsers

GET /users

获取用户列表
List all users

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|

> Response Examples

> Success

```json
{
  "statusCode": 200,
  "data": {
    "users": [
      {
        "username": "admin",
        "roles": [
          "IT Operator",
          "byoc"
        ],
        "creator": "admin",
        "permissions": [
          "checkpoint:all",
          "inference:all",
          "role:all",
          "sagemaker_endpoint:all",
          "train:all",
          "user:all"
        ],
        "password": "********"
      },
      {
        "username": "username",
        "roles": [
          "IT Operator"
        ],
        "creator": "admin",
        "permissions": [
          "checkpoint:all",
          "inference:all",
          "role:all",
          "sagemaker_endpoint:all",
          "train:all",
          "user:all"
        ],
        "password": "********"
      }
    ],
    "previous_evaluated_key": "not_applicable",
    "last_evaluated_key": "not_applicable"
  },
  "message": "OK"
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

HTTP Status Code **200**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» data|object|true|none||none|
|»» users|[object]|true|none||none|
|»»» username|string|true|none||none|
|»»» roles|[string]|true|none||none|
|»»» creator|string|true|none||none|
|»»» permissions|[string]|true|none||none|
|»»» password|string|true|none||none|
|»» previous_evaluated_key|string|true|none||none|
|»» last_evaluated_key|string|true|none||none|
|» message|string|true|none||none|

<a id="opIdCreateUser"></a>

## POST 创建用户 CreateUser

POST /users

创建新用户
Create a new user

> Body Parameters

```json
{
  "username": "username",
  "password": "XXXXXXXXXXXXX",
  "creator": "admin",
  "roles": [
    "IT Operator",
    "Designer"
  ]
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|
|body|body|object| no |none|
|» username|body|string| yes |用户名（User Name）|
|» roles|body|[string]| yes |角色列表（Roles）|
|» creator|body|string| yes |创建者用户名（Creator User Name）|
|» permissions|body|[string]| yes |权限列表（Permissions）|
|» password|body|string| yes |密码（Password）|

> Response Examples

> Created

```json
{
  "statusCode": 201,
  "message": "Created"
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|201|[Created](https://tools.ietf.org/html/rfc7231#section-6.3.2)|Created|Inline|

### Responses Data Schema

HTTP Status Code **201**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» message|string|true|none||none|

<a id="opIdDeleteUser"></a>

## DELETE 删除用户 DeleteUsers

DELETE /users

删除用户
Delete users

> Body Parameters

```json
{
  "user_name_list": [
    "string"
  ]
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|
|body|body|object| no |none|
|» user_name_list|body|[string]| yes |用户名列表（User Name List）|

> Response Examples

> 204 Response

```json
{}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|204|[No Content](https://tools.ietf.org/html/rfc7231#section-6.3.5)|No Content|Inline|

### Responses Data Schema

# 模型文件（Checkpoints）

<a id="opIdCreateCheckpoint"></a>

## POST 通过URL上传模型文件 CreateCheckpoint

POST /checkpoints

通过URL上传模型文件
Create a new Checkpoint by URL

> Body Parameters

```json
{
  "checkpoint_type": "ControlNet",
  "params": {
    "message": "placeholder for chkpts upload test",
    "creator": "admin"
  },
  "urls": [
    "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_canny.pth"
  ]
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|
|body|body|object| no |none|
|» checkpoint_type|body|string| yes |模型文件类型（Checkpoint Type）|
|» params|body|object| yes |参数（Params）|
|»» message|body|string| yes |模型文件信息（Message）|
|»» creator|body|string| yes |创建者用户名（Creator User Name）|
|» urls|body|[string]| yes |URLs|

> Response Examples

> Accepted

```json
{
  "statusCode": 202,
  "message": "Checkpoint creation in progress, please check later"
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|202|[Accepted](https://tools.ietf.org/html/rfc7231#section-6.3.3)|Accepted|Inline|

### Responses Data Schema

HTTP Status Code **202**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» data|object|true|none||none|
|»» checkpoint|object|true|none||none|
|»»» id|string|true|none||none|
|»»» type|string|true|none||none|
|»»» s3_location|string|true|none||none|
|»»» status|string|true|none||none|
|»»» params|object|true|none||none|
|»»»» message|string|true|none||none|
|»»»» creator|string|true|none||none|
|»»»» created|string|true|none||none|
|»»»» multipart_upload|object|true|none||none|
|»»»»» v1-5-pruned-emaonly.safetensors2|object|true|none||none|
|»»»»»» upload_id|string|true|none||none|
|»»»»»» bucket|string|true|none||none|
|»»»»»» key|string|true|none||none|
|»» s3PresignUrl|object|true|none||none|
|»»» v1-5-pruned-emaonly.safetensors2|[string]|true|none||none|
|» message|string|true|none||none|

<a id="opIdListCheckpoints"></a>

## DELETE 删除模型文件 DeleteCheckpoints

DELETE /checkpoints

删除模型文件
Delete checkpoints

> Body Parameters

```json
{
  "checkpoint_id_list": [
    "string"
  ]
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|
|body|body|object| no |none|
|» checkpoint_id_list|body|[string]| yes |模型文件ID列表（ID List）|

> Response Examples

> 204 Response

```json
{}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|204|[No Content](https://tools.ietf.org/html/rfc7231#section-6.3.5)|No Content|Inline|

### Responses Data Schema

<a id="opIdUpdateCheckpoint"></a>

## PUT 更新模型文件状态 UpdateCheckpoint

PUT /checkpoints/{id}

更新模型文件状态
Update Checkpoint

> Body Parameters

```json
{
  "checkpoint_id": "5b47fc8f-c1b0-47ad-9d85-ad0f08526e28",
  "status": "Active",
  "multi_parts_tags": {
    "v1-5-pruned-emaonly.safetensors": [
      {
        "ETag": "\"e6279f0ad8bf8048c0d106095c4d4b24\"",
        "PartNumber": 1
      },
      {
        "ETag": "\"01a458e7d019140cb792b577596b7918\"",
        "PartNumber": 2
      },
      {
        "ETag": "\"296e59a1fb1ea02f6512c5b4c4565bea\"",
        "PartNumber": 3
      },
      {
        "ETag": "\"9dd22961ddf32130a22b36dc53f93fd0\"",
        "PartNumber": 4
      },
      {
        "ETag": "\"bfb91caed0e9f1aaaca7a0f125e7e96b\"",
        "PartNumber": 5
      }
    ]
  }
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|id|path|string| yes |none|
|body|body|object| no |none|
|» checkpoint_id|body|string| yes |模型文件ID（Checkpoint ID）|
|» status|body|string| yes |状态（Status）|
|» multi_parts_tags|body|object| yes |ETags|
|»» v1-5-pruned-emaonly.safetensors|body|[object]| yes |none|
|»»» ETag|body|string| yes |none|
|»»» PartNumber|body|integer| yes |none|

> Response Examples

> Success

```json
{
  "statusCode": 200,
  "headers": {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
  },
  "checkpoint": {
    "id": "d613760c-c8f7-466a-9838-cea3033bf57d",
    "type": "Stable-diffusion",
    "s3_location": "s3://******/Stable-diffusion/checkpoint/custom/d613760c-c8f7-466a-9838-cea3033bf57d",
    "status": "Initial",
    "params": {
      "creator": "admin",
      "multipart_upload": {
        "v1-5-pruned-emaonly.safetensors": {
          "bucket": "******",
          "upload_id": "KFzbB7FwAuCDkR3NRaAO81uNM6E38KrvbB9m9T2dPlE0XUbOXrDB0c9CbhpLA3wFqnN6uTf0qh7HOYOmSXFwicHYOL7XfPMAhsT0cbxRhWvbyKPo8bO_wXrFcbUMDY.ef4vFZNKfdKaRba23Src44CrwGtYjkp3RQ8dEZubjleVTTTz0gaclwjfxmrdpqcZa",
          "key": "Stable-diffusion/checkpoint/custom/d613760c-c8f7-466a-9838-cea3033bf57d/v1-5-pruned-emaonly.safetensors"
        }
      },
      "message": "api-test-message",
      "created": "2023-12-07 00:45:59.334826"
    }
  }
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

HTTP Status Code **200**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||Status Code|
|» headers|object|true|none||none|
|»» Access-Control-Allow-Headers|string|true|none||none|
|»» Access-Control-Allow-Origin|string|true|none||none|
|»» Access-Control-Allow-Methods|string|true|none||none|
|» checkpoint|object|true|none||Checkpoint|
|»» id|string|true|none||ID|
|»» type|string|true|none||Type|
|»» s3_location|string|true|none||S3 Key|
|»» status|string|true|none||Status|
|»» params|object|true|none||none|
|»»» creator|string|true|none||User Name|
|»»» multipart_upload|object|true|none||S3 Multipart Upload|
|»»»» v1-5-pruned-emaonly.safetensors|object|true|none||none|
|»»»»» bucket|string|true|none||none|
|»»»»» upload_id|string|true|none||none|
|»»»»» key|string|true|none||none|
|»»» message|string|true|none||Message|
|»»» created|string|true|none||Created At|

# 推理端点（Endpoints）

<a id="opIdListEndpoints"></a>

## GET 获取端点列表 ListEndpoints

GET /endpoints

获取推理端点列表
List inference endpoints

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|

> Response Examples

> Success

```json
{
  "statusCode": 200,
  "data": {
    "endpoints": [
      {
        "EndpointDeploymentJobId": "d1253aa5-c884-4989-a7d1-d8806bc4fa59",
        "autoscaling": false,
        "max_instance_number": "1",
        "startTime": "2024-01-30 07:59:46.842717",
        "status": null,
        "instance_type": "ml.g4dn.2xlarge",
        "current_instance_count": "1",
        "endTime": "2024-01-30 08:03:33.991793",
        "endpoint_status": "InService",
        "endpoint_name": "esd-real-time-api-test",
        "error": null,
        "endpoint_type": "Real-time",
        "owner_group_or_role": [
          "byoc"
        ]
      },
      {
        "EndpointDeploymentJobId": "a50ba02e-057f-433d-83be-0f52fdd45b13",
        "autoscaling": true,
        "max_instance_number": "1",
        "startTime": "2024-01-26 08:19:52.759748",
        "status": null,
        "instance_type": "ml.g4dn.xlarge",
        "current_instance_count": "0",
        "endTime": "2024-02-02 03:58:32.946464",
        "endpoint_status": "InService",
        "endpoint_name": "esd-async-api-test",
        "error": null,
        "endpoint_type": "Async",
        "owner_group_or_role": [
          "IT Operator"
        ]
      }
    ]
  },
  "message": "OK"
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

HTTP Status Code **200**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» data|object|true|none||none|
|»» endpoints|[object]|true|none||none|
|»»» EndpointDeploymentJobId|string|true|none||none|
|»»» autoscaling|boolean|true|none||none|
|»»» max_instance_number|string|true|none||none|
|»»» startTime|string|true|none||none|
|»»» status|null|true|none||none|
|»»» instance_type|string|true|none||none|
|»»» current_instance_count|string|true|none||none|
|»»» endTime|string|true|none||none|
|»»» endpoint_status|string|true|none||none|
|»»» endpoint_name|string|true|none||none|
|»»» error|null|true|none||none|
|»»» endpoint_type|string|true|none||none|
|»»» owner_group_or_role|[string]|true|none||none|
|» message|string|true|none||none|

<a id="opIdCreateEndpoint"></a>

## POST 创建端点 CreateEndpoint

POST /endpoints

创建推理端点
Create Endpoint

> Body Parameters

```json
{
  "endpoint_name": "test",
  "instance_type": "ml.g5.2xlarge",
  "initial_instance_count": "1",
  "autoscaling_enabled": false,
  "assign_to_roles": [
    "Designer",
    "IT Operator"
  ],
  "creator": "admin"
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|
|body|body|object| no |none|
|» endpoint_name|body|string| no |端点名称（Endpoint Name）|
|» endpoint_type|body|string| yes |端点类型（Endpoint Type）|
|» instance_type|body|string| yes |实例类型（Instance Type）|
|» initial_instance_count|body|string| yes |初始实例数（Initial Instance Count）|
|» autoscaling_enabled|body|boolean| yes |开启 Autoscaling（Enable Autoscaling）|
|» assign_to_roles|body|[string]| yes |角色列表（Role List）|
|» creator|body|string| yes |创建者用户名（Creator User Name）|

> Response Examples

> Success

```json
{
  "statusCode": 200,
  "message": "Endpoint deployment started: infer-endpoint-prod",
  "data": {
    "EndpointDeploymentJobId": "60b12a2e-c54d-496c-b405-1bc77b17e2f9",
    "autoscaling": false,
    "max_instance_number": "1",
    "startTime": "2023-12-07 01:08:43.410628",
    "status": null,
    "current_instance_count": "0",
    "endTime": null,
    "endpoint_status": "Creating",
    "endpoint_name": "infer-endpoint-prod",
    "error": null,
    "owner_group_or_role": [
      "Designer",
      "IT Operator"
    ]
  }
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

HTTP Status Code **200**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» message|string|true|none||none|
|» data|[Endpoint](#schemaendpoint)|true|none||none|
|»» EndpointDeploymentJobId|string|true|none||ID|
|»» autoscaling|boolean|true|none||Autoscaling Enabled|
|»» max_instance_number|string|true|none||Max Instance Count|
|»» startTime|string|true|none||Start Time|
|»» current_instance_count|integer|true|none||Current Instance Count|
|»» endTime|string|true|none||End Time|
|»» endpoint_status|string|true|none||Endpoint Status|
|»» endpoint_name|string|true|none||Endpoint Name|
|»» error|null|true|none||Error Message|
|»» owner_group_or_role|[string]|true|none||Roles|

<a id="opIdDeleteEndpoints"></a>

## DELETE 删除端点 DeleteEndpoints

DELETE /endpoints

删除推理端点
Delete endpoints

> Body Parameters

```json
{
  "delete_endpoint_list": [
    "infer-endpoint-test"
  ],
  "username": "admin"
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| yes |none|
|body|body|object| no |none|
|» delete_endpoint_list|body|[string]| yes |端点名列表（Endpoint Name List）|
|» username|body|string| yes |用户名（User Name）|

> Response Examples

> 200 Response

```json
{}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

# 推理（Inferences）

<a id="opIdCreateInferenceJob"></a>

## POST 创建推理作业 CreateInferenceJob

POST /inferences

创建推理作业，创建成功后，需要通过返回的`api_params_s3_upload_url` 上传推理参数
Create inference, When you got response, you have to upload your Payload to `api_params_s3_upload_url`

> Body Parameters

```json
{
  "user_id": "admin",
  "inference_type": "Async",
  "task_type": "txt2img",
  "models": {
    "Stable-diffusion": [
      "v1-5-pruned-emaonly.safetensors"
    ],
    "VAE": [
      "Automatic"
    ],
    "embeddings": []
  },
  "filters": {
    "createAt": 1707141090.135923,
    "creator": "sd-webui"
  }
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|body|body|object| no |none|
|» user_id|body|string| yes |用户名（User Name）|
|» inference_type|body|string| yes |推理类型（Inference Type）Async | Real-time|
|» task_type|body|string| yes |任务类型（Task Type）txt2img | img2img | rembg|
|» models|body|object| yes |模型列表（Model List）|
|»» Stable-diffusion|body|[string]| yes |none|
|»» VAE|body|[string]| yes |none|
|»» embeddings|body|[string]| yes |none|
|» filters|body|object| yes |将在下一版本中移除|
|»» createAt|body|number| yes |none|
|»» creator|body|string| yes |none|

> Response Examples

> Success

```json
{
  "statusCode": 201,
  "data": {
    "inference": {
      "id": "f3421ce5-9ab9-40a2-b33b-3f126de70a52",
      "type": "txt2img",
      "api_params_s3_location": "s3://xxxx/txt2img/infer_v2/f3421ce5-9ab9-40a2-b33b-3f126de70a52/api_param.json",
      "api_params_s3_upload_url": "https://xxxx.s3.amazonaws.com/txt2img/infer_v2/f3421ce5-9ab9-40a2-b33b-3f126de70a52/api_param.json?AWSAccessKeyId=xxxxx&Signature=HNp81KZy2%2FDSgz7%2FWP%2FdMIUPz8s%3D&x-amz-security-token=xxxxx",
      "models": [
        {
          "id": "32a7af23-3763-4289-a6af-2156a2331878",
          "name": [
            "v1-5-pruned-emaonly.safetensors"
          ],
          "type": "Stable-diffusion"
        },
        {
          "id": "VAE",
          "name": [
            "Automatic"
          ],
          "type": "VAE"
        }
      ]
    }
  },
  "message": "Created"
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

HTTP Status Code **200**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» data|object|true|none||none|
|»» inference|object|true|none||none|
|»»» id|string|true|none||none|
|»»» type|string|true|none||none|
|»»» api_params_s3_location|string|true|none||none|
|»»» api_params_s3_upload_url|string|true|none||none|
|»»» models|[object]|true|none||none|
|»»»» id|string|true|none||none|
|»»»» name|[string]|true|none||none|
|»»»» type|string|true|none||none|
|» message|string|true|none||none|

<a id="opIdListInferenceJobs"></a>

## DELETE 删除推理作业 DeleteInferenceJobs

DELETE /inferences

删除推理作业列表
Delete inference jobs

> Body Parameters

```json
{
  "inference_id_list": [
    "99"
  ]
}
```

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|Authorization|header|string| no |none|
|body|body|object| no |none|
|» inference_id_list|body|[string]| yes |推理作业ID列表（Inference Job ID List）|

> Response Examples

> No Content

```json
{}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|204|[No Content](https://tools.ietf.org/html/rfc7231#section-6.3.5)|No Content|Inline|

### Responses Data Schema

<a id="opIdRunInferenceJob"></a>

## PUT 开始推理作业 StartInferenceJob

PUT /inferences/{jobId}/start

开始推理作业
Start inference job

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|jobId|path|string| yes |推理作业ID（Inference Job ID）|
|Authorization|header|string| yes |none|

> Response Examples

> Success

```json
{
  "statusCode": 202,
  "data": {
    "inference": {
      "inference_id": "f3421ce5-9ab9-40a2-b33b-3f126de70a52",
      "status": "inprogress",
      "endpoint_name": "esd-async-97fce5e",
      "output_path": "s3://elonniu/sagemaker_output/48159016-c040-4b49-8a1c-b57445946918.out"
    }
  },
  "message": "Accepted"
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

HTTP Status Code **200**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» data|object|true|none||none|
|»» inference|object|true|none||none|
|»»» inference_id|string|true|none||none|
|»»» status|string|true|none||none|
|»»» endpoint_name|string|true|none||none|
|»»» output_path|string|true|none||none|
|» message|string|true|none||none|

<a id="opIdGetInferenceJob"></a>

## GET 获取推理作业详情 GetInferenceJob

GET /inferences/{jobId}

获取指定的推理作业详情
Gets a specific infernece job

### Params

|Name|Location|Type|Required|Description|
|---|---|---|---|---|
|jobId|path|string| yes |推理作业ID（Inference Job ID）|
|Authorization|header|string| yes |none|

> Response Examples

> Success

```json
{
  "statusCode": 200,
  "data": {
    "img_presigned_urls": [
      "https://xxxx.s3.amazonaws.com/out/9d93e241-745a-4464-bb99-22253c910a01/result/image_0.png?AWSAccessKeyId=xxxxx&Signature=%2BIoU%2BUuY0oJmd9yb8B6xJGnRN3Q%3D&x-amz-security-token=xxxxx"
    ],
    "output_presigned_urls": [
      "https://xxxx.s3.amazonaws.com/out/9d93e241-745a-4464-bb99-22253c910a01/result/9d93e241-745a-4464-bb99-22253c910a01_param.json?AWSAccessKeyId=xxxxx&Signature=sAi%2ByxVsUBdZfSh34QCMAh%2B2jGg%3D&x-amz-security-token=xxxxx"
    ],
    "inference_info_name": "/tmp/9d93e241-745a-4464-bb99-22253c910a01_param.json",
    "startTime": "2024-02-05 06:10:52.552528",
    "taskType": "txt2img",
    "completeTime": "2024-02-05 06:10:56.270528",
    "params": {
      "input_body_presign_url": "https://xxxx.s3.amazonaws.com/txt2img/infer_v2/9d93e241-745a-4464-bb99-22253c910a01/api_param.json?AWSAccessKeyId=xxxx&Signature=i8q7mM74oZoqtl6reQCPEklgXkc%3D&x-amz-security-token=xxxxx",
      "used_models": {
        "Stable-diffusion": [
          {
            "s3": "s3://xxxx/Stable-diffusion/checkpoint/custom/32a7af23-3763-4289-a6af-2156a2331878",
            "id": "32a7af23-3763-4289-a6af-2156a2331878",
            "model_name": "v1-5-pruned-emaonly.safetensors",
            "type": "Stable-diffusion"
          }
        ],
        "VAE": [
          {
            "s3": "None",
            "id": "VAE",
            "model_name": "Automatic",
            "type": "VAE"
          }
        ]
      },
      "input_body_s3": "s3://xxxx/txt2img/infer_v2/9d93e241-745a-4464-bb99-22253c910a01/api_param.json",
      "sagemaker_inference_instance_type": "ml.g4dn.2xlarge",
      "sagemaker_inference_endpoint_id": "9ef3c8bf-936e-47bb-a6da-e11e43140fb1",
      "sagemaker_inference_endpoint_name": "esd-real-time-9ef3c8b"
    },
    "InferenceJobId": "9d93e241-745a-4464-bb99-22253c910a01",
    "status": "succeed",
    "inference_type": "Real-time",
    "createTime": "2024-02-05 06:10:52.299624",
    "image_names": [
      "image_0.png"
    ],
    "owner_group_or_role": [
      "admin"
    ]
  },
  "message": "OK"
}
```

### Responses

|HTTP Status Code |Meaning|Description|Data schema|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Success|Inline|

### Responses Data Schema

HTTP Status Code **200**

|Name|Type|Required|Restrictions|Title|description|
|---|---|---|---|---|---|
|» statusCode|integer|true|none||none|
|» data|object|true|none||none|
|»» img_presigned_urls|[string]|true|none||none|
|»» output_presigned_urls|[string]|true|none||none|
|»» inference_info_name|string|true|none||none|
|»» startTime|string|true|none||none|
|»» taskType|string|true|none||none|
|»» completeTime|string|true|none||none|
|»» params|object|true|none||none|
|»»» input_body_presign_url|string|true|none||none|
|»»» used_models|object|true|none||none|
|»»»» Stable-diffusion|[object]|true|none||none|
|»»»»» s3|string|false|none||none|
|»»»»» id|string|false|none||none|
|»»»»» model_name|string|false|none||none|
|»»»»» type|string|false|none||none|
|»»»» VAE|[object]|true|none||none|
|»»»»» s3|string|false|none||none|
|»»»»» id|string|false|none||none|
|»»»»» model_name|string|false|none||none|
|»»»»» type|string|false|none||none|
|»»» input_body_s3|string|true|none||none|
|»»» sagemaker_inference_instance_type|string|true|none||none|
|»»» sagemaker_inference_endpoint_id|string|true|none||none|
|»»» sagemaker_inference_endpoint_name|string|true|none||none|
|»» InferenceJobId|string|true|none||none|
|»» status|string|true|none||none|
|»» inference_type|string|true|none||none|
|»» createTime|string|true|none||none|
|»» image_names|[string]|true|none||none|
|»» owner_group_or_role|[string]|true|none||none|
|» message|string|true|none||none|

# Data Schema

<h2 id="tocS_Checkpoint">Checkpoint</h2>

<a id="schemacheckpoint"></a>
<a id="schema_Checkpoint"></a>
<a id="tocScheckpoint"></a>
<a id="tocscheckpoint"></a>

```json
{
  "id": "string",
  "s3Location": "string",
  "type": "string",
  "status": "string",
  "name": [
    "string"
  ],
  "created": 0,
  "allowed_roles_or_users": [
    "string"
  ]
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|id|string|true|none||none|
|s3Location|string|true|none||none|
|type|string|true|none||none|
|status|string|true|none||none|
|name|[string]|true|none||none|
|created|number|true|none||none|
|allowed_roles_or_users|[string]|true|none||none|

<h2 id="tocS_Endpoint">Endpoint</h2>

<a id="schemaendpoint"></a>
<a id="schema_Endpoint"></a>
<a id="tocSendpoint"></a>
<a id="tocsendpoint"></a>

```json
{
  "EndpointDeploymentJobId": "string",
  "autoscaling": true,
  "max_instance_number": "string",
  "startTime": "string",
  "current_instance_count": 0,
  "endTime": "string",
  "endpoint_status": "string",
  "endpoint_name": "string",
  "error": null,
  "owner_group_or_role": [
    "string"
  ]
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|EndpointDeploymentJobId|string|true|none||ID|
|autoscaling|boolean|true|none||Autoscaling Enabled|
|max_instance_number|string|true|none||Max Instance Count|
|startTime|string|true|none||Start Time|
|current_instance_count|integer|true|none||Current Instance Count|
|endTime|string|true|none||End Time|
|endpoint_status|string|true|none||Endpoint Status|
|endpoint_name|string|true|none||Endpoint Name|
|error|null|true|none||Error Message|
|owner_group_or_role|[string]|true|none||Roles|

<h2 id="tocS_User">User</h2>

<a id="schemauser"></a>
<a id="schema_User"></a>
<a id="tocSuser"></a>
<a id="tocsuser"></a>

```json
{
  "username": "string",
  "roles": [
    "string"
  ],
  "creator": "string",
  "permissions": [
    "string"
  ],
  "password": "string"
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|username|string|true|none||用户名（User Name）|
|roles|[string]|true|none||角色列表（Roles）|
|creator|string|true|none||创建者用户名（Creator User Name）|
|permissions|[string]|true|none||权限列表（Permissions）|
|password|string|true|none||密码（Password）|

<h2 id="tocS_InferenceJob">InferenceJob</h2>

<a id="schemainferencejob"></a>
<a id="schema_InferenceJob"></a>
<a id="tocSinferencejob"></a>
<a id="tocsinferencejob"></a>

```json
{
  "inference_info_name": "string",
  "startTime": "string",
  "taskType": "string",
  "completeTime": "string",
  "params": {
    "input_body_presign_url": "string",
    "used_models": {
      "Stable-diffusion": [
        {
          "s3": "string",
          "id": "string",
          "model_name": "string",
          "type": "string"
        }
      ],
      "Lora": [
        {
          "s3": "string",
          "id": "string",
          "model_name": "string",
          "type": "string"
        }
      ]
    },
    "input_body_s3": "string",
    "output_path": "string",
    "sagemaker_inference_endpoint_id": "string",
    "sagemaker_inference_endpoint_name": "string"
  },
  "InferenceJobId": "string",
  "status": "string",
  "sagemakerRaw": "string",
  "image_names": [
    "string"
  ],
  "owner_group_or_role": [
    "string"
  ]
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|inference_info_name|string|true|none||Inference Info Name|
|startTime|string|true|none||Start Time|
|taskType|string|true|none||Task Type|
|completeTime|string|true|none||Complete Time|
|params|object|true|none||Params|
|» input_body_presign_url|string|true|none||none|
|» used_models|object|true|none||none|
|»» Stable-diffusion|[object]|true|none||none|
|»»» s3|string|false|none||none|
|»»» id|string|false|none||none|
|»»» model_name|string|false|none||none|
|»»» type|string|false|none||none|
|»» Lora|[object]|true|none||none|
|»»» s3|string|false|none||none|
|»»» id|string|false|none||none|
|»»» model_name|string|false|none||none|
|»»» type|string|false|none||none|
|» input_body_s3|string|true|none||none|
|» output_path|string|true|none||none|
|» sagemaker_inference_endpoint_id|string|true|none||none|
|» sagemaker_inference_endpoint_name|string|true|none||none|
|InferenceJobId|string|true|none||Inference Job Id|
|status|string|true|none||Status|
|sagemakerRaw|string|true|none||Sagemaker Raw|
|image_names|[string]|true|none||Images Array|
|owner_group_or_role|[string]|true|none||Roles|

<h2 id="tocS_Model">Model</h2>

<a id="schemamodel"></a>
<a id="schema_Model"></a>
<a id="tocSmodel"></a>
<a id="tocsmodel"></a>

```json
{
  "id": "string",
  "model_name": "string",
  "created": 0,
  "params": {
    "create_model_params": {
      "shared_src": "string",
      "extract_ema": true,
      "from_hub": true,
      "new_model_name": "string",
      "ckpt_path": "string",
      "train_unfrozen": true,
      "new_model_url": "string",
      "is_512": true,
      "new_model_token": "string"
    },
    "resp": {
      "config_dict": {
        "lr_factor": 0,
        "lora_weight": 0,
        "epoch_pause_frequency": 0,
        "lr_power": 0,
        "model_path": "string",
        "resolution": 0,
        "save_lora_for_extra_net": true,
        "num_train_epochs": 0,
        "infer_ema": true,
        "save_state_after": true,
        "use_shared_src": [
          true
        ],
        "has_ema": true,
        "gradient_set_to_none": true,
        "weight_decay": 0,
        "save_ckpt_after": true,
        "save_lora_cancel": true,
        "save_lora_during": true,
        "noise_scheduler": "string",
        "prior_loss_weight": 0,
        "save_embedding_every": 0,
        "use_ema": true,
        "lr_scheduler": "string",
        "concepts_path": "string",
        "hflip": true,
        "stop_text_encoder": 0,
        "train_imagic": true,
        "snapshot": "string",
        "cache_latents": true,
        "lr_scale_pos": 0,
        "deterministic": true,
        "lifetime_revision": 0,
        "use_concepts": true,
        "epoch": 0,
        "gradient_accumulation_steps": 0,
        "mixed_precision": "string",
        "pretrained_model_name_or_path": "string",
        "strict_tokens": true,
        "lora_unet_rank": 0,
        "save_safetensors": true,
        "model_dir": "string",
        "custom_model_name": "string",
        "disable_logging": true,
        "save_ckpt_cancel": true,
        "gradient_checkpointing": true,
        "prior_loss_weight_min": 0,
        "freeze_clip_normalization": true,
        "lr_warmup_steps": 0,
        "lora_txt_weight": 0,
        "pad_tokens": true,
        "use_subdir": true,
        "epoch_pause_time": 0,
        "train_unet": true,
        "lr_cycles": 0,
        "v2": true,
        "clip_skip": 0,
        "txt_learning_rate": 0,
        "max_token_length": 0,
        "concepts_list": [
          "string"
        ],
        "save_ema": true,
        "save_lora_after": true,
        "tenc_grad_clip_norm": 0,
        "split_loss": true,
        "model_name": "string",
        "train_unfrozen": true,
        "save_state_during": true,
        "tomesd": 0,
        "ema_predict": true,
        "tenc_weight_decay": 0,
        "revision": 0,
        "train_batch_size": 0,
        "shuffle_tags": true,
        "save_state_cancel": true,
        "use_lora": true,
        "initial_revision": 0,
        "offset_noise": 0,
        "graph_smoothing": 0,
        "dynamic_img_norm": true,
        "scheduler": "string",
        "half_model": true,
        "sample_batch_size": 0,
        "sanity_seed": 0,
        "optimizer": "string",
        "learning_rate_min": 0,
        "shared_diffusers_path": "string",
        "lora_learning_rate": 0,
        "prior_loss_scale": true,
        "prior_loss_target": 0,
        "src": "string",
        "pretrained_vae_name_or_path": "string",
        "lora_txt_learning_rate": 0,
        "save_ckpt_during": true,
        "use_lora_extended": true,
        "save_preview_every": 0,
        "attention": "string",
        "lora_model_name": "string",
        "lora_txt_rank": 0,
        "sanity_prompt": "string",
        "learning_rate": 0,
        "lora_use_buggy_requires_grad": true,
        "disable_class_matching": true
      },
      "response": [
        {}
      ],
      "s3_output_location": "string"
    }
  },
  "status": "string",
  "output_s3_location": "string"
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|id|string|true|none||ID|
|model_name|string|true|none||Model Name|
|created|number|true|none||Created At|
|params|object|true|none||Parameters|
|» create_model_params|object|true|none||none|
|»» shared_src|string|true|none||none|
|»» extract_ema|boolean|true|none||none|
|»» from_hub|boolean|true|none||none|
|»» new_model_name|string|true|none||none|
|»» ckpt_path|string|true|none||none|
|»» train_unfrozen|boolean|true|none||none|
|»» new_model_url|string|true|none||none|
|»» is_512|boolean|true|none||none|
|»» new_model_token|string|true|none||none|
|» resp|object|true|none||none|
|»» config_dict|object|true|none||none|
|»»» lr_factor|number|true|none||none|
|»»» lora_weight|integer|true|none||none|
|»»» epoch_pause_frequency|integer|true|none||none|
|»»» lr_power|integer|true|none||none|
|»»» model_path|string|true|none||none|
|»»» resolution|integer|true|none||none|
|»»» save_lora_for_extra_net|boolean|true|none||none|
|»»» num_train_epochs|integer|true|none||none|
|»»» infer_ema|boolean|true|none||none|
|»»» save_state_after|boolean|true|none||none|
|»»» use_shared_src|[boolean]|true|none||none|
|»»» has_ema|boolean|true|none||none|
|»»» gradient_set_to_none|boolean|true|none||none|
|»»» weight_decay|number|true|none||none|
|»»» save_ckpt_after|boolean|true|none||none|
|»»» save_lora_cancel|boolean|true|none||none|
|»»» save_lora_during|boolean|true|none||none|
|»»» noise_scheduler|string|true|none||none|
|»»» prior_loss_weight|number|true|none||none|
|»»» save_embedding_every|integer|true|none||none|
|»»» use_ema|boolean|true|none||none|
|»»» lr_scheduler|string|true|none||none|
|»»» concepts_path|string|true|none||none|
|»»» hflip|boolean|true|none||none|
|»»» stop_text_encoder|integer|true|none||none|
|»»» train_imagic|boolean|true|none||none|
|»»» snapshot|string|true|none||none|
|»»» cache_latents|boolean|true|none||none|
|»»» lr_scale_pos|number|true|none||none|
|»»» deterministic|boolean|true|none||none|
|»»» lifetime_revision|integer|true|none||none|
|»»» use_concepts|boolean|true|none||none|
|»»» epoch|integer|true|none||none|
|»»» gradient_accumulation_steps|integer|true|none||none|
|»»» mixed_precision|string|true|none||none|
|»»» pretrained_model_name_or_path|string|true|none||none|
|»»» strict_tokens|boolean|true|none||none|
|»»» lora_unet_rank|integer|true|none||none|
|»»» save_safetensors|boolean|true|none||none|
|»»» model_dir|string|true|none||none|
|»»» custom_model_name|string|true|none||none|
|»»» disable_logging|boolean|true|none||none|
|»»» save_ckpt_cancel|boolean|true|none||none|
|»»» gradient_checkpointing|boolean|true|none||none|
|»»» prior_loss_weight_min|number|true|none||none|
|»»» freeze_clip_normalization|boolean|true|none||none|
|»»» lr_warmup_steps|integer|true|none||none|
|»»» lora_txt_weight|integer|true|none||none|
|»»» pad_tokens|boolean|true|none||none|
|»»» use_subdir|boolean|true|none||none|
|»»» epoch_pause_time|integer|true|none||none|
|»»» train_unet|boolean|true|none||none|
|»»» lr_cycles|integer|true|none||none|
|»»» v2|boolean|true|none||none|
|»»» clip_skip|integer|true|none||none|
|»»» txt_learning_rate|number|true|none||none|
|»»» max_token_length|integer|true|none||none|
|»»» concepts_list|[string]|true|none||none|
|»»» save_ema|boolean|true|none||none|
|»»» save_lora_after|boolean|true|none||none|
|»»» tenc_grad_clip_norm|integer|true|none||none|
|»»» split_loss|boolean|true|none||none|
|»»» model_name|string|true|none||none|
|»»» train_unfrozen|boolean|true|none||none|
|»»» save_state_during|boolean|true|none||none|
|»»» tomesd|integer|true|none||none|
|»»» ema_predict|boolean|true|none||none|
|»»» tenc_weight_decay|number|true|none||none|
|»»» revision|integer|true|none||none|
|»»» train_batch_size|integer|true|none||none|
|»»» shuffle_tags|boolean|true|none||none|
|»»» save_state_cancel|boolean|true|none||none|
|»»» use_lora|boolean|true|none||none|
|»»» initial_revision|integer|true|none||none|
|»»» offset_noise|integer|true|none||none|
|»»» graph_smoothing|integer|true|none||none|
|»»» dynamic_img_norm|boolean|true|none||none|
|»»» scheduler|string|true|none||none|
|»»» half_model|boolean|true|none||none|
|»»» sample_batch_size|integer|true|none||none|
|»»» sanity_seed|integer|true|none||none|
|»»» optimizer|string|true|none||none|
|»»» learning_rate_min|number|true|none||none|
|»»» shared_diffusers_path|string|true|none||none|
|»»» lora_learning_rate|number|true|none||none|
|»»» prior_loss_scale|boolean|true|none||none|
|»»» prior_loss_target|integer|true|none||none|
|»»» src|string|true|none||none|
|»»» pretrained_vae_name_or_path|string|true|none||none|
|»»» lora_txt_learning_rate|number|true|none||none|
|»»» save_ckpt_during|boolean|true|none||none|
|»»» use_lora_extended|boolean|true|none||none|
|»»» save_preview_every|integer|true|none||none|
|»»» attention|string|true|none||none|
|»»» lora_model_name|string|true|none||none|
|»»» lora_txt_rank|integer|true|none||none|
|»»» sanity_prompt|string|true|none||none|
|»»» learning_rate|number|true|none||none|
|»»» lora_use_buggy_requires_grad|boolean|true|none||none|
|»»» disable_class_matching|boolean|true|none||none|
|»» response|[oneOf]|true|none||none|

oneOf

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|»»» *anonymous*|object|false|none||none|
|»»»» visible|boolean|false|none||none|
|»»»» choices|[string]|false|none||none|
|»»»» value|string|false|none||none|
|»»»» __type__|string|false|none||none|

xor

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

xor

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|»»» *anonymous*|integer|false|none||none|

continued

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|»» s3_output_location|string|true|none||none|
|status|string|true|none||Status|
|output_s3_location|string|true|none||Output S3 Location|

<h2 id="tocS_Tag">Tag</h2>

<a id="schematag"></a>
<a id="schema_Tag"></a>
<a id="tocStag"></a>
<a id="tocstag"></a>

```json
{
  "id": 1,
  "name": "string"
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|id|integer(int64)|false|none||Tag ID|
|name|string|false|none||Tag Name|

<h2 id="tocS_TrainJob">TrainJob</h2>

<a id="schematrainjob"></a>
<a id="schema_TrainJob"></a>
<a id="tocStrainjob"></a>
<a id="tocstrainjob"></a>

```json
{
  "id": "string",
  "modelName": "string",
  "status": "string",
  "trainType": "string",
  "created": 0,
  "sagemakerTrainName": "string"
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|id|string|true|none||ID|
|modelName|string|true|none||Model Name|
|status|string|true|none||Status|
|trainType|string|true|none||Train Type|
|created|number|true|none||Created At|
|sagemakerTrainName|string|true|none||Sagemaker Train Name|

<h2 id="tocS_Category">Category</h2>

<a id="schemacategory"></a>
<a id="schema_Category"></a>
<a id="tocScategory"></a>
<a id="tocscategory"></a>

```json
{
  "id": 1,
  "name": "string"
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|id|integer(int64)|false|none||Category ID|
|name|string|false|none||Category Name|

<h2 id="tocS_Role">Role</h2>

<a id="schemarole"></a>
<a id="schema_Role"></a>
<a id="tocSrole"></a>
<a id="tocsrole"></a>

```json
{
  "role_name": "string",
  "creator": "string",
  "permissions": [
    "string"
  ]
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|role_name|string|true|none||角色名（Role Name）|
|creator|string|true|none||创建者用户名（Creator User Name）|
|permissions|[string]|true|none||权限列表（Permissions）|

<h2 id="tocS_Pet">Pet</h2>

<a id="schemapet"></a>
<a id="schema_Pet"></a>
<a id="tocSpet"></a>
<a id="tocspet"></a>

```json
{
  "id": 1,
  "category": {
    "id": 1,
    "name": "string"
  },
  "name": "doggie",
  "photoUrls": [
    "string"
  ],
  "tags": [
    {
      "id": 1,
      "name": "string"
    }
  ],
  "status": "available"
}

```

### Attribute

|Name|Type|Required|Restrictions|Title|Description|
|---|---|---|---|---|---|
|id|integer(int64)|true|none||Pet ID|
|category|[Category](#schemacategory)|true|none||group|
|name|string|true|none||name|
|photoUrls|[string]|true|none||image URL|
|tags|[[Tag](#schematag)]|true|none||tag|
|status|string|true|none||Pet Sales Status|

#### Enum

|Name|Value|
|---|---|
|status|available|
|status|pending|
|status|sold|

