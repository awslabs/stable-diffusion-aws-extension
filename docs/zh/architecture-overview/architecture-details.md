以下的图表简单展示了所提供的插件和中间件之间的交互过程。用户仍旧可以在单独的EC2/本地服务器上安装并启动社区WebUI并在此基础上安装我们的插件，原有模型融合，训练和推理部分负载则通过在AWS账户中所安装的中间件提供的RESTful API迁移到AWS服务。请注意，中间件是基于AWS账户粒度的，这意味着它可以作为工作节点单独安装，同作为控制节点的WebUI进行通信。用户只需要输入每个账户的API URL和API密钥，中间件将会决定使用哪个特定的AWS账户来执行后续的工作。

![workflow](../images/workflow.png)
<center>整体工作流程</center>

中间件对外提供RESTful API，以符合OpenAPI规范帮助WebUI插件与AWS云服务（Amazon SageMaker、S3等）进行交互，主要功能包括请求身份验证，请求分发（比如SageMaker.jumpstart/model/predictor/estimator/tuner/utils等）模型训练，模型推理等生命周期管理工作。下图是中间件的整体架构:

![middleware](../images/middleware.png)
<center>中间件架构</center>

- 在WebUI控制台中的用户将使用分配的API token触发对API Gateway的请求，同时进行身份验证。（注：WebUI的角度不需要AWS凭证。）
- API Gateway将根据URL前缀将请求路由到不同功能的Lambda函数，以实现相应任务（例如，模型上传、checkpoint合并）、模型训练和模型推理。同时，Lambda函数将操作元数据记录到DynamoDB中（例如，推断参数、模型名称），以便进行后续查询和关联。
- 在训练过程中，Step Function将被调用来安排训练过程，其中包括使用Amazon SageMaker进行训练和使用SNS进行训练状态通知。在推理过程中，Lambda函数将调用Amazon SageMaker来实现异步推断。训练数据、模型和checkpoint将以不同的前缀分隔存储在S3存储桶中。

为了使插件中的容器镜像与社区保持同步，我们构建了CI/CD自动化流程（如下图所示）来自动跟踪社区提交并打包和构建新的容器镜像，用户可以轻松启动最新的扩展而无需任何手动操作。

![cicd](../images/cicd.png)
<center>Image CI/CD Workflow</center>