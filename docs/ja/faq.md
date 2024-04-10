
# よくある質問

## 一般

**Q: Extension for Stable Diffusion on AWS とは何ですか ?** 

*Extension for Stable Diffusion on AWS* は、Stable Diffusion WebUI のモデルトレーニング、推論、微調整のワークロードを、ローカルサーバーから Amazon SageMaker に移行するのを支援することを目的とした AWS ソリューションです。拡張機能と AWSCloudFormation テンプレートを提供することで、柔軟なクラウドリソースを活用し、モデルの反復処理を加速し、単一サーバーデプロイに関連するパフォーマンスボトルネックを軽減します。

**Q: このソリューションが対応している Stable Diffusion WebUI の標準機能/サードパーティ拡張機能は何ですか ?** 

このソリューションは、Stable Diffusion WebUI の多くの標準機能/サードパーティ拡張機能に対応しています。詳細は[機能と利点 ](./solution-overview/features-and-benefits.md) をご確認ください。

**Q: このソリューションのライセンスは何ですか ?** 

このソリューションは [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) ライセンスの下で提供されています。これは Apache Software Foundation が記述した許可ベースのフリーソフトウェアライセンスです。ユーザーがソフトウェアを目的のために使用、配布、変更し、ロイヤリティの心配なく変更版を配布することを許可しています。

**Q: 機能要求やバグレポートはどのように提出できますか ?** 

GitHub の issue を通して機能要求やバグレポートを提出できます。[機能要求のテンプレート ](https://github.com/awslabs/stable-diffusion-aws-extension/issues/new?assignees=&labels=feature-request%2Cneeds-triage&projects=&template=feature_request.yml&title=%28module+name%29%3A+%28short+issue+description%29) と[バグレポートのテンプレート ](https://github.com/awslabs/stable-diffusion-aws-extension/issues/new?assignees=&labels=bug%2Cneeds-triage&projects=&template=bug_report.yml&title=%28module+name%29%3A+%28short+issue+description%29) をご覧ください。

## インストールと設定

**Q: サードパーティプラグインとこのソリューションのプラグインをインストールする際に特定の順序はありますか ?** 

現在のところ、このソリューションがサポートするサードパーティ拡張機能をまずインストールし、その後にこのソリューションの拡張機能をインストールすることをお勧めしています。ただし、インストール順序は変更できます。その場合、機能が正常に動作するために WebUI の再起動が必要です。

**Q: WebUI を正常にインストールした後、ブラウザからアクセスできません。どのように解決すればよいですか ?** 

ブラウザで WebUI リンクにアクセスする前に、必要なポートがオープンでファイアウォールによってブロックされていないことを確認してください。

**Q: どのようにこのソリューションを更新できますか ?** 

現在、CloudFormation を介してスタックをデプロイすることで、頻繁にソリューションを更新することはお勧めしません。更新が必要な場合は、既存のソリューションスタックをアンインストールし、新しいスタックを CloudFormation テンプレートに基づいてデプロイすることをお勧めします。今後のすべての CloudFormation デプロイでは、'Bucket' フィールドに前回のデプロイで使用した S3 バケット名を入力し、'DeployedBefore' を 'yes' に選択することで、CloudFormation の再デプロイを確実に行えます。

**Q: 同じコンピューター上で別のログインユーザーに切り替えるにはどうすればよいですか ?** 

新しいシークレットブラウザウィンドウを開き、別のユーザー資格情報でログインすることで、ユーザーを切り替えることができます。

**Q: ローカルの推論オプションを削除し、WebUI がクラウド推論のみをサポートするようにするにはどうすればよいですか ?** 

WebUI を開き、**設定** タブに移動し、左側のセッションバーの*ユーザーインターフェイス*セクションを選択します。`[info] Quick settings list (setting entries that appear at the top of page rather than in settings tab) (requires Reload UI)` フィールドを見つけ、'sd_model_checkpoint' のチェックを外します。その後、'設定を適用'をクリックし、WebUI をターミナルから再読み込みします。WebUI を再読み込みすると、左上の checkpoint 選択ドロップダウンリストが消え、ユーザーはクラウド推論オプションのみを使用できるようになります。
![generate-lock-step](images/generate-lock-step.png) 

## 価格

**Q: このソリューションの使用料はどのように請求されますか ?** 

このソリューションは無料で使用できます。使用する AWS サービスのコストのみ負担することになります。最小料金やセットアップ料金はありません。詳細なコストについては[コスト見積もり](./cost.md) を参照してください。
