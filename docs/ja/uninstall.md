# Extension for Stable Diffusion on AWS をアンインストールする

!!!Warning " 警告"
    ソリューションをアンインストールする前に、[メインタブ ](./user-guide/CloudAssetsManage.md) の「デプロイされたエンドポイントを削除する」を参照して、このソリューションによってデプロイされたすべての Amazon SageMaker エンドポイントを手動で削除してください。ソリューションをアンインストールすると、モデルのトレーニング、ファインチューニング、推論のログと関係性を示す DynamoDB テーブル、AWS Lambda 関数、AWS ステップ機能などが同時に削除されます。

Extension for Stable Diffusion on AWS をアンインストールするには、AWS CloudFormation スタックを削除する必要があります。

AWS Management Console または AWS Command Line Interface (AWS CLI) を使用して CloudFormation スタックを削除できます。

## AWS Management Console を使ってスタックをアンインストールする

1. [AWS CloudFormation][cloudformation-console] コンソールにサインインします。
2. このソリューションのインストール親スタックを選択します。
3. 「削除」を選択します。

## AWS Command Line Interface を使ってスタックをアンインストールする

AWS Command Line Interface (AWS CLI) が環境で利用可能かどうかを確認してください。インストール手順については、*AWS CLI ユーザーガイド*の [AWS Command Line Interface とは ][aws-cli] を参照してください。AWS CLI が利用可能であることを確認したら、次のコマンドを実行してください。

```bash 
aws cloudformation delete-stack --stack-name <installation-stack-name> --region <aws-region> 
``` 


[cloudformation-console]: https://console.aws.amazon.com/cloudformation/home 
[aws-cli]: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html 
