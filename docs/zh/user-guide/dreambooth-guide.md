# 打开Dreambooth面板

![Dreambooth tab](../../images/open-dreambooth-tab.png)

# 创建模型

* 选择Create From Cloud面板 
![Creat model tab](../../images/open-create-model-tab.png)

* 输入模型名称，请注意格式要求，只能包含字母数字和“-”
![Enter model name](../../images/enter-model-name.png)

* 选择checkpoint文件，包含两种形式，以local开头的是本地存储的checkpoint文件，以cloud开头的是存储在S3上的checkpoint文件
![Select checkpoint](../../images/select-checkpoint.png)

* 首次使用可以选择local checkpoint文件
![Select local checkpoint](../../images/select-local-checkpoint.png)

* 点击Create Model From Cloud按钮，开始创建模型
![Click create model button](../../images/click-create-model-button.png)

# 选择模型
* 选择Select From Cloud面板 
![Select model tab](../../images/open-select-model-tab.png)

* 选择模型
![Select model tab](../../images/select-model.png)
* 设置训练参数
![Input setting](../../images/input-setting.png)
* 设置训练数据
![Input dataset](../../images/input-dataset.png)
![Input prompt](../../images/input-prompt.png)

# 训练
* 点击SageMaker训练按钮
![Click train button](../../images/click-sagemaker-train.png)
* 训练完成后可以收到邮件通知，并且在inference tab中可以加载训练完成的模型
![Load trained model step1](../../images/load-trained-model-1.png)
![Load trained model step2](../../images/load-trained-model-2.png)
