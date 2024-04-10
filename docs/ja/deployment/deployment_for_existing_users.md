
ソリューションを起動する前に、このガイドで説明されているアーキテクチャ、サポートされているリージョン、および他の考慮事項を確認してください。この節の手順に従ってソリューションをあなたのアカウントに設定してデプロイしてください。

**デプロイ所要時間**: 約 20 分

## 前提条件
- ユーザーは事前に Linux システムを実行するコンピューターを用意する必要があります。
- [aws cli](https://aws.amazon.com/cli/)をインストールして設定する。
- 以前のバージョンの Stable Diffusion WebUI AWS プラグインをデプロイする。

## デプロイの概要
以下の手順に従ってこのソリューションを AWS にデプロイしてください。

- ステップ 1: Stable Diffusion WebUI を更新する
- ステップ 2: AWS コンソールにログインし、CloudFormation の既存の Stable Diffusion AWS 拡張機能テンプレートを更新する

## デプロイの手順

### ステップ 1 - Linux: Stable Diffusion WebUI を更新する (Linux)
1. [リンク](https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml)から CloudFormation テンプレートをダウンロードする
2. [AWS マネジメントコンソール](https://console.aws.amazon.com/)にサインインし、[CloudFormation コンソール](https://console.aws.amazon.com/cloudformation/)に移動する
3. [スタック]ページで、[スタックの作成]を選択し、[新しいリソース(標準)の作成]を選択する
4. [テンプレートの指定]ページで、[テンプレートが準備済み]を選択し、[テンプレートファイルのアップロード]を選択し、ステップ1でダウンロードしたテンプレートを参照して選択し、[次へ]を選択する
5. [スタックの詳細の指定]ページで、スタック名をスタック名ボックスに入力し、[次へ]を選択する
6. [スタックオプションの設定]ページで、[次へ]を選択する
7. [確認]ページで、スタックの詳細を確認し、[送信]を選択する
8. スタックの作成が完了するまで待つ
9. CloudFormation スタックの出力値を見つけ、[WebUIURL]の値のリンクをクリックして WebUI にアクセスする。スタックが正常に作成された後、内部設定が完了するまで約 30 分待つ必要があります。

### ステップ 1 - Windows: Stable Diffusion WebUI を更新する (Windows)
1. Windows サーバーを起動し、RDP でログインする
2. [このリンク](https://docs.aws.amazon.com/en_us/AWSEC2/latest/WindowsGuide/install-nvidia-driver.html)を参照して NVIDIA ドライバーをインストールする
3. [Python ウェブサイト](https://www.python.org/downloads/release/python-3106/)にアクセスし、Python をダウンロードしてインストールする。インストール時に "Python をパスに追加する" をチェックする
4. [Git ウェブサイト](https://git-scm.com/download/win)にアクセスし、Git をダウンロードしてインストールする
5. PowerShell を開き、`git clone https://github.com/awslabs/stable-diffusion-aws-extension`を実行してこのプロジェクトのソースコードをダウンロードする
6. ソースコードディレクトリ内で、`install.bat`を実行する
7. ダウンロードした `stable-diffusion-webui` フォルダ内で、`webui-user.bat`を実行する

### ステップ 2: CloudFormation の既存の Stable Diffusion AWS 拡張機能テンプレートを更新する
1. [AWS マネジメントコンソール](https://console.aws.amazon.com/)にログインする
2. サービスメニューから "CloudFormation" を選択し、このソリューションに展開されたスタックを見つけ、それを選択し、右上の [更新] をクリックする
3. [スタックの更新] で [現在のテンプレートの置き換え] を選択し、最新の CloudFormation の[リンク](https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json)を "Amazon S3 URL" に入力し、[次へ]をクリックする
4. [スタックオプションの設定] で [次へ]をクリックする
5. [確認] で承認オプションを選択し、[送信]をクリックする
6. CloudFormation がスタックの更新を開始します。これには時間がかかる場合があります。[スタック]ページでスタックの状況を監視できます。

## 注意
1. SageMaker の Inference Endpoints は、ソリューションを V1.5.0 にアップデートした後に削除して新しく展開する必要があります。
2. WebUI とミドルウェアのバージョンは一致する必要があります。
3. EC2 に新しい WebUI をデプロイするのを推奨します。 
4. ミドルウェア API バージョン 1.4.0 は直接更新できますが、バージョン 1.3.0 は先にアンインストールしてから再インストールする必要があります。
5. API を介してすでに統合されているサービスがある場合は、[アップグレードの認証検証](https://awslabs.github.io/stable-diffusion-aws-extension/zh/developer-guide/api_authentication/)方法について API ドキュメントを確認し、本番環境に移行する前に十分にテストを行ってください。
