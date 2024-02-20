### 异步推理
- 通过 `CreateInferenceJob` 创建推理作业
- 根据 `CreateInferenceJob` 返回的预签名地址 `api_params_s3_upload_url` 上传推理参数
- 通过 `StartInferenceJob` 开始推理作业
- 通过 `GetInferenceJob` 获取推理作业，检查状态，成功则停止请求


### 实时推理
- 通过 `CreateInferenceJob` 创建推理作业
- 根据 `CreateInferenceJob` 返回的预签名地址 `api_params_s3_upload_url` 上传推理参数
- 通过 `StartInferenceJob` 开始推理作业，实时推理作业会在本接口获得推理结果
