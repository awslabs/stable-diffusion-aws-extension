
--- 
title: カスタムコンテナ
language_tabs: 
- shell: シェル
language_clients: 
- shell: "" 
toc_footers: [] 
Includes: [] 
HeadingLevel: 2 

--- 

<!-- Generator: Widdershins v4.0.1 --> 

<h1 id="stable-diffusion-train-and-deploy-api"> カスタムコンテナ </h1> 

# 概要

**Extension for Stable Diffusion on AWS** は非常に柔軟です。SageMaker エンドポイントモデルのコンテナイメージをいつでも置き換えることができます。

この機能を実現するには、次の手順に従います:

- ステップ 1: コンテナイメージのビルド
- ステップ 2: カスタムコンテナイメージを使用してエンドポイントを作成
- ステップ 3: コンテナイメージが機能しているかを確認または診断

<br> 

# コンテナイメージのビルド

独自のコンテナイメージを構築し、ソリューションがデプロイされているリージョンの [Amazon ECR](https://console.aws.amazon.com/ecr) にアップロードすることができます。[AWS CLI での Amazon ECR の使用 ](https://docs.aws.amazon.com/ja_jp/AmazonECR/latest/userguide/getting-started-cli.html) を参照してください。操作が完了すると、ECR URI が取得できます。例:

```shell 
{your_account_id}.dkr.ecr.{region}.amazonaws.com/your-image:latest 
``` 

Dockerfile テンプレート:

```dockerfile 
# ソリューションによって作成されたイメージをベースイメージとして使用することをお勧めします。
FROM {your_account_id}.dkr.ecr.{region}.amazonaws.com/stable-diffusion-aws-extension/aigc-webui-inference:latest 

# 拡張機能をダウンロード
RUN mkdir -p /opt/ml/code/extensions/ && \ 
   cd /opt/ml/code/extensions/ && \ 
   git clone https://github.com/**.git 

``` 

<br> 

# カスタムコンテナイメージを使用してエンドポイントを作成

`byoc` という名前のロールを作成し、ログインしたユーザーをそのロールに追加して、以下の画像に示す機能を有効にします:

![UpdateImage](../images/byoc.png) 


<br> 

# コンテナイメージが機能しているかを確認または診断

コンテナイメージが置き換わった後、SageMaker エンドポイントのログを確認して、コンテナイメージが正しく機能しているかを確認するか、問題の原因を診断することができます:

- **{region}**: ソリューションがデプロイされている地域、例 : `us-east-1` 
- **{endpoint-name}**: エンドポイント名、例 : `esd-type-111111` 

```shell 
https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups$3FlogGroupNameFilter$3D{endpoint-name} 
``` 
