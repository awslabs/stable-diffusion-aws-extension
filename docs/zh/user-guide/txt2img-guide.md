# 打开Sagemaker Inference面板

![Sagemaker Inference面板](../images/open-sagemaker-inference-2.png)

# 部署推理节点

* 选择推理实例类型和数目，然后点击deploy, 可以在右边状态窗口看到"Endpoint deployment started. Please wait..."的提示信息。
![Choose resource](../images/deploy-endpoint.png)
![Deploy message](../images/deploy-init-info.png)

* 点击"Select Cloud SageMaker Endpoint"旁边的刷新按钮，然后查看当前的部署任务，名字的格式是"推理节点名字+部署状态：Creating/Failed/InService+部署结束时间"
![Choose resource](../images/deploy-status.png)

* 等待大概10分钟时间，可以看到推理节点的状态变成Inservice
![Finish deploy](../images/finish-deploy.png)


