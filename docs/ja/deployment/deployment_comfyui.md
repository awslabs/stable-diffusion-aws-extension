ソリューションをデプロイする前に、このガイドのアーキテクチャ図とリージョンサポートに関する情報を確認することをお勧めします。次に、以下の手順に従ってソリューションを構成し、アカウントにデプロイしてください。

デプロイ時間: 約20分。

## デプロイの概要
このソリューション(ComfyUIの部分)をAmazon Web Servicesにデプロイする際の主なプロセスは以下の通りです。

- ステップ1: ソリューションのミドルウェアをデプロイする。
- ステップ2: ComfyUIフロントエンドをデプロイする。

!!! tip
        デプロイ時の問題が発生した場合は、FAQ章のComfyUIセクションを参照してください。

## デプロイ手順
### ステップ 1: ソリューションのミドルウェアをデプロイする
この自動化された Amazon CloudFormation テンプレートは、Amazon Web Services にソリューションをデプロイします。

1. [AWS Management Console](https://console.aws.amazon.com/) にサインインし、[Extension for Stable Diffusion on AWS](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json){:target="_blank"} を使用してスタックを作成します。
2. デフォルトでは、このテンプレートはコンソールにログインした後、デフォルトのリージョンで起動します。このソリューションを指定の Amazon Web Services リージョンで起動するには、コンソールのナビゲーションバーのリージョンドロップダウンリストから目的のリージョンを選択してください。
3. 「Create Stack」ページで、正しいテンプレート URL が「Amazon S3 URL」テキストボックスに入力されていることを確認し、「Next」を選択します。
4. 「Specify stack details」ページで、ソリューションスタックに一意のアカウント内名前を割り当て、命名要件を満たします。デプロイパラメータについては下の表を参照してください。「Next」をクリックします。

    |パラメータ|説明|推奨事項|
    |:-------------|:--------------|:--------------|
    |Bucket|有効な新しい S3 バケット名を入力するか、このソリューションの ComfyUI セクションで以前にデプロイされた S3 バケットの名前を入力します||
    |email|通知を受け取る有効な電子メールアドレスを入力します||
    |SdExtensionApiKey|数字と文字で構成される 20 文字の文字列を入力してください|デフォルトは "09876543210987654321" です|
    |LogLevel|希望する Lambda ログ出力レベルを選択します|デフォルトは ERROR のみ出力されます|

5. 「Specify Stack Options」ページで、「Next」を選択します。
6. 「Review」ページで設定を確認し、確定します。テンプレートが AWS Identity and Access Management (IAM) リソースを作成することを認める確認チェックボックスが選択されていることを確認します。また、AWS CloudFormation に必要なその他の機能のチェックボックスが選択されていることを確認します。「Submit」を選択してスタックをデプロイします。
7. AWS CloudFormation コンソールの「Status」列でスタックのステータスを確認できます。約 15 分で「CREATE_COMPLETE」ステータスを受け取るはずです。

    !!! tip
        「AWS Notification - Subscription Confirmation」という件名のメールを予約済みの受信トレイで速やかに確認し、指示に従って「Confirm subscription」リンクをクリックして購読を完了してください。


### ステップ2: ComfyUIフロントエンドのデプロイ
ステップ2では、顧客向けにComfyUIフロントエンドをインストールします。このフロントエンドには、中国語の現地化プラグインとワークフローをクラウドに公開するためのボタンが自動的に含まれており、顧客により使いやすいUIインターフェイスを提供します。この自動化されたAmazon CloudFormationテンプレートは、Amazon Web Servicesにデプロイされます。

1. [AWS Management Console](https://console.aws.amazon.com/)にログインし、コンソールの右上隅にある**Create Stack**をクリックし、**With new resource (standard)** を選択すると、スタックの作成ページにリダイレクトされます。
2. **Create Stack**ページで、**Choose an existing template**を選択し、**Specify template**エリアで**Amazon S3 URL**を選択し、この[デプロイメントテンプレートリンク](https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/comfy.yaml)を入力してから**Next**を選択します。
3. **Specify Stack Details**ページで、ソリューションスタックの一意の名前をアカウントに割り当て、命名要件を満たします。**Parameters**セクションでは、デプロイパラメータの説明は次のとおりです。**Next**をクリックします。

    !!! tip
        ここでのEC2キーペアは、主にEC2へのローカルリモート接続に使用されます。既存のものがない場合は、[公式マニュアル](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html){:target="_blank"}を参照して作成できます。

    |パラメータ|説明|推奨事項|
    |:-------------|:--------------|:--------------|
    |InstanceType |デプロイされるEC2のインスタンスタイプ|アニメーション、動画などの推論を含む場合はG6、G5インスタンスを推奨|
    |NumberOfInferencePorts|推論環境の数|5を超えないことを推奨|
    |StackName|ステップ1で正常にデプロイされたスタックの名前||
    |keyPairName|既存のEC2キーペアを選択||

4. **Configure Stack Options**ページで、**Next**を選択します。
5. **Review**ページで設定を確認し、確認します。テンプレートがAmazon Identity and Access Management (IAM)リソースを作成することを確認するチェックボックスをオンにしてください。また、AWS CloudFormationが必要なその他の機能を実行することを確認するチェックボックスをオンにしてください。**Submit**を選択してスタックをデプロイします。
6. AWS CloudFormationコンソールの**Status**列でスタックの状態を確認できます。約3分以内に**CREATE_COMPLETE**ステータスを受け取るはずです。
7. 正常にデプロイされたスタックを選択し、**Outputs**を開き、**Designer**に対応するリンクをクリックしてソリューションによってデプロイされたComfyUIフロントエンドを開きます。Designerにアクセスする際は、VPNを無効にするか、ポート10000を削除する必要がある場合があります。**NumberOfInferencePortsStart**は推論環境の開始ポートアドレスを表し、デプロイ数に応じてポートアドレスが増加します。例えば、NumberOfInferencePortsが2に設定されている場合、アクセス可能な推論環境アドレスは次のとおりです: http://EC2Address:10001、http://EC2Address:10002。

    |役割|機能|ポート|
    |:-------------|:--------------|:--------------|
    |リードアーティスト/ワークフローマネージャー|新しいカスタムノードをインストールし、EC2でワークフローをデバッグし、ワークフローと環境をAmazon SageMakerに公開できます。また、SageMakerリソースを呼び出し、公開されたワークフローを選択して推論検証を行うこともできます。| http://EC2Address|
    |通常のアーティスト|このポートからインターフェースで、リードアーティストが公開したワークフローを選択し、推論パラメータを変更し、"Prompt on AWS"をチェックし、Amazon SageMakerを呼び出して推論を行うことができます。|NumberOfInferencePortsが3に設定されている場合、アクセス可能な推論環境アドレスの範囲は次のとおりです: <ul><li>http://EC2Address:10001</li><li>http://EC2Address:10002</li><li>http://EC2Address:10003</li></ul>|

    !!! tip
        初回デプロイ後は、少し待つ必要がある場合があります。リンクを開いたときに "Comfy is Initializing or Starting" というプロンプトが表示された場合、バックエンドがComfyUIを初期化している状態です。しばらく待ってからページを更新して確認してください。


### Step 3: Debug and create a usable workflow on the ComfyUI page.
You can refer to the "Debugging Workflows" subsection in [this guide](../user-guide/ComfyUI/inference.md)

### Step 4: Deploy new Amazon SageMaker inference endpoint
After successfully completing step 1, you need to deploy the required Amazon SageMaker inference nodes using API. Subsequent deployments of new ComfyUI workflow inferences will utilize the computational resources of these inference nodes.

The `ApiGatewayUrl` and `ApiGatewayUrlToken` required in the following API code can be found in the **Outputs** tab of the stack deployed successfully in step 1.

Please open any command-line interface capable of running code, such as Terminal on a local MacBook, and execute the following API code.

```
curl --location ‘YourAPIURL/endpoints’ \
--header ‘x-api-key: Your APIkey’ \
--header ‘username: api’ \
--header ‘Content-Type: application/json’ \
--data-raw ‘{
    “workflow_name”:“Please fill the name of template you just released“,
    “endpoint_name”: “When you don't need to associate it with a workflow, you should fill in the name of the inference endpoint you want to create",
    “service_type”: “comfy”,
    “endpoint_type”: “Async”,
    “instance_type”: “instance type”,
    “initial_instance_count”: 1,
    “min_instance_number”: 1,
    “max_instance_number”: 2,
    “autoscaling_enabled”: true,
    “assign_to_roles”: “test”
    “assign_to_roles”: [ “test” ]
}’
```

!!! Important 
    If your workflow is relatively complex, it's important to select asynchronous inference node types. Otherwise, you may encounter timeout issues due to the service's maximum wait time of 30 seconds for synchronous calls.



Delete corresponding Amazon SageMaker endpoint, can be executed as below:
```
curl --location --request DELETE 'https://please fill ApiGatewayUrl/endpoints' \
--header 'username: api' \
--header 'x-api-key: please type the ApiGatewayUrlToken' \
--header 'Content-Type: application/json' \
--data-raw '{
    "endpoint_name_list": [
        "comfy-real-time-test-34"//type the name of the endpoint
    ]
}'
```

!!! Important
    It's not recommended to directly delete endpoints from the SageMaker console as it can potentially lead to inconsistencies in data.






