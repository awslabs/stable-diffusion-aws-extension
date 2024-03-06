### 通过 URL 上传
- 请求 `CreateCheckpoint`

### 通过文件上传
- 请求 `CreateCheckpoint` 创建模型文件
- 通过 S3 预签名地址上传文件
- 通过 `UpdateCheckpoint` 更新状态
