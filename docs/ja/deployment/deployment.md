ソリューションを起動する前に、このガイドで説明されているアーキテクチャ、対応地域、その他の考慮事項を確認してください。このセクションのステップバイステップの手順に従って、アカウントにソリューションを構成およびデプロイしてください。

**デプロイ時間**: 約 20 分です。

## 前提条件
ユーザーは事前に Linux システムが動作するコンピューターを用意する必要があります。

## デプロイの概要

AWS 上にこのソリューションをデプロイするには、次の手順に従ってください。

- ステップ 0: Stable Diffusion webUI をデプロイする(まだ Stable Diffusion webUI をデプロイしていない場合)。
- ステップ1: ミドルウェアとしてソリューションをデプロイする。
- ステップ 2: API URL と API トークンを構成する。

!!!Important "注意" 
    このソリューションには2つの使用オプションがあります: UI インターフェイスを通じて、およびバックエンド API を直接呼び出すことで。ステップ0は、ユーザーが UI インターフェイスを使う場合にのみ実行する必要があります。このステップには別のオープンソースプロジェクトである Stable Diffusion webUI のインストールが含まれており、これにより業務操作を webUI から実行できるようになります。

## デプロイの手順

### ステップ 0 - Linux: Stable Diffusion WebUI をデプロイする(Linux)

1. [AWS Management Console](https://console.aws.amazon.com/)にサインインし、[WebUI on EC2](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml)を使用してスタックを作成します。
2. 「 Create Stack 」ページで「 Next 」を選択します。
3. 「 Specify stack details 」ページで、スタック名を Stack name ボックスに入力し、パラメーターを必要に応じて調整してから、「 Next 」を選択します。
4. 「 Configure stack options 」ページで「 Next 」を選択します。
5. 「 Review 」ページで、スタックの詳細を確認し、必要に応じて機能を確認し、「 Submit 」を選択します。
6. スタックの作成が完了するまで待ちます。
7. CloudFormation スタックの出力値を見つけ、「 WebUIURL 」の値のリンクをクリックして WebUI にアクセスします。スタックが正常に作成された後、内部設定が完了するまで約 30 分待つ必要があることに注意してください。

### ステップ 0 - Windows: Stable Diffusion WebUI をデプロイする(Windows)

1. Windows サーバーを起動し、RDP を使ってログインします。
2. [このリンク](https://docs.aws.amazon.com/en_us/AWSEC2/latest/WindowsGuide/install-nvidia-driver.html)を参照して、NVIDIA ドライバーをインストールします。
3. [Python ウェブサイト](https://www.python.org/downloads/release/python-3106/)にアクセスし、Python をダウンロードしてインストールします。インストール中に「 Python をパスに追加する」をチェックしてください。
4. [Git ウェブサイト](https://git-scm.com/download/win)にアクセスし、Git をダウンロードしてインストールします。
5. PowerShell を開き、`git clone https://github.com/awslabs/stable-diffusion-aws-extension`を実行してこのプロジェクトのソースコードをダウンロードします。
6. ソースコードディレクトリ内で`install.bat`を実行します。
7. ダウンロードした`stable-diffusion-webui`フォルダ内で`webui-user.bat`を実行します。

### ステップ1: ミドルウェアとしてソリューションをデプロイする

この AWS CloudFormation テンプレートを使用すると、ソリューションを AWS クラウド上に自動的にデプロイできます。

1. [AWS Management Console](https://console.aws.amazon.com/)にサインインし、[Launch solution in AWS Standard Regions](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json)を使用して AWS CloudFormation テンプレートを起動します。
2. テンプレートはコンソールにログインするときのデフォルト リージョンで起動されます。別の AWS リージョンでこのソリューションを起動するには、コンソールのナビゲーションバーでリージョンセレクターを使用します。
3. 「 Create stack 」ページで、「 Amazon S3 URL 」テキストボックスに正しいテンプレート URL が表示されていることを確認し、「次へ」を選択します。
4. 「 Specify stack details 」ページで、ソリューションスタックに有効で一意のアカウントレベルの名前を割り当てます。
5. 「 Parameters 」ページで、このソリューションで使用する新しい有効なバケット名を「 Bucket 」の下に入力します。「 email 」の下に通知を受け取るための正しい電子メールアドレスを入力します。「 LogLevel 」の下で、出力したい Amazon ログレベルを選択します。デフォルトでは ERROR ログのみが出力されます。「 SdExtensionApiKey 」の下に、英数字の組み合わせで 20 文字の文字列を入力します。デフォルトでは 0987654321098765432 です。「次へ」を選択します。

    !!!Important "注意" 
        ソリューションチームに確認する前は、「 EcrImageTag 」を変更しないでください。

6. 「 Configure stack options 」ページで「次へ」を選択します。
7. 「 Review 」ページで、設定を確認して承認します。AWS Identity and Access Management (IAM)リソースが作成されることを確認するチェックボックスをオンにします。「 Create stack 」を選択してスタックをデプロイします。

AWSCloudFormation コンソールの「 Status 」列でスタックの状態を確認できます。約 15 分で CREATE_COMPLETE ステータスが表示されるはずです。

!!!Important "注意" 
    以前に設定したメールアドレスの受信箱を確認し、件名が「 AWS Notification - Subscription Confirmation 」