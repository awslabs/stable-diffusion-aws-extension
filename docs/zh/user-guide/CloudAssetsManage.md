本章节将详细介绍本解决方案提供的便捷云上资源管理方式。

## 上传训练模型
如需在txt2img或img2img使用非云端推理模型，您可以选择按下列两种方式的步骤完成推理模型上传，即可按[txt2img](./txt2img-guide.md)或[img2img](./img2img-guide.md)相应步骤完成模型调用及推理。

### 从原生webUI上传模型至云上
考虑到用户多样的使用场景，本方式适用于将webUI前端部署在非本地电脑的其他机器上的场景。同于webUI社区原生使用方式，用户需要首先将相关模型上传至部署了webUI前端的机器上，对应webUI项目文件夹下、models子文件夹的对应处，之后即可跟从下面步骤完成模型上传到云上。

1. 进入解决方案主标签页**Amazon SageMaker**，找到**Cloud Assents Management**模块。
2. 选择Upload Model to S3 from WebUI下拉框, 该方式表示从部署WebUI服务的models文件路径上传模型。
![Upload Models to S3](../images/Upload-models-old.png)
3. 在对应的模型输入部署WebUI服务的models文件路径地址。
> **提示**: 您可以通过在文本框中输入多个本地模型路径来上传多种模型。
4. 点击**Upload Models to Cloud**，启动模型上传。
5. 上传完成后，会在左侧**Label**看到提示。


### 从本地机器上传模型至云上
考虑到用户多样的使用场景，本方式适用于将webUI前端部署在本地电脑上的场景。

1. 进入解决方案主标签页**Amazon SageMaker**，找到**Cloud Assents Management**模块。
2. 选择Upload Model to S3 from Laptop, 该方式表示从访问WebUI的本地路径上传模型。
![Upload Models to S3](../images/Upload-models-new.png)
3. 选择要上传的模型类型，目前支持六种：SD Checkpoints, Textual Inversion, LoRA model, ControlNet model, Hypernetwork, VAE
4. 本地选择要上传的模型文件。
> **提示**: 您可以多选模型文件，但受制于浏览器限制，最好选择的文件数不要超过10个，总大小不要超过8g。
5. 点击**Upload Models to Cloud**，启动模型上传。
6. 上传会依据文件大小与数量异步分片上传，各分片上传完成后，会在**选择文件**按钮下看到提示。



## Amazon SageMaker推理节点管理

### 部署推理节点

1. 进入解决方案主标签页**Amazon SageMaker**，找到**Cloud Assents Management**模块的**Deploy New SageMaker Endpoint**区域。
2. 为简化用户部署步骤，本解决方案默认endpoint配置为机型ml.g5.2xlarge，实例数量1的自动弹性的推理节点。如果用户有额外需求，可以勾选**Advanced Endpoint Configuration**，勾选框下方即会展示更多可选参数，包括endpoint自主命名、机型及实例数量。同时，用户可以通过是否勾选**Enable Autoscaling**来指示新部署endpoint是否需要弹性伸缩功能。所有参数选择完成后，点击**Deploy**。
3. 您可进入**txt2img**或**img2img**的**Amazon SageMaker Inference**模块的下拉菜单**Select Cloud SageMaker Endpoint**，刷新并看到当前所有推理节点的部署状态。
> **补充：** 推理节点列表的名字的格式是：推理节点名字+部署状态：Creating/Failed/InService+部署结束时间。
4. 等待大约10分钟，即可看到最新推理节点的状态变成**InService**，表明推理节点部署成功。


### 删除已部署推理节点
1. 进入解决方案主标签页**Amazon SageMaker**，点击**Select Cloud SageMaker Endpoint**列表右侧刷新按钮，刷新下拉列表，选择需要删除的推理节点。
2. 点击**Delete**，左侧**Label**处会显示提示信息，完成推理节点删除。



## AWS数据集管理

### 数据集上传
在模型微调等功能中，需要输入一个图片集，用以微调工作。该功能模块助力用户快速上传图片集到云端。

1. 进入解决方案主标签页**Amazon SageMaker**，**AWS Dataset Management**区块，**Create**标签页。
![Create Dataset to S3](../images/Dataset-management.png)

2. 点击**Click to Upload a File**，在弹出的本地文件列表中，确认选中一次模型微调所需的所有图片。
3. 在**Dataset Name**输入该图片文件夹的名字，在**Dataset Description**输入该数据集的描述，点击**Create Dataset**。
4. 等待几秒，下方的**Create Result**区域显示**Complete Dataset XXXX creation**，即表示该数据集已经成功上传到云上。

### 数据集浏览
数据集上传完成后，通过此功能模块，能够帮助用户快速得到数据集对应的云上地址。用户可以复制此地址，粘贴到对应需要上传图片集的地址位置。

1. 进入解决方案主标签页**Amazon SageMaker**，**AWS Dataset Management**区块，**Browse**标签页。
2. 刷新**Dataset From Cloud**列表，选择需要浏览的图片集名称。
3. 等待几秒，**dataset s3 location**区域即会显示该数据集的云上S3地址，复制粘贴即可取用，做后续步骤。

