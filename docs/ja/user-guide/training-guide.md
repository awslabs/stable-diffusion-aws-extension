# 訓練ガイド

この訓練は [Kohya-SS](https://github.com/kohya-ss/sd-scripts) に基づいています。Kohya-SS は、一般的な GPU でも使えるように設計され、Stable Diffusion WebUI と互換性がある、Stable Diffusion モデルの微調整用の Python ライブラリです。このソリューションは、SDXL 及び SD 1.5 上で LoRA 訓練を行うことができます。

## 訓練ユーザーガイド
![Kohya Training](../images/Kohya_training.png) 

### 基礎モデルの準備
**Model** のドロップダウンリストを更新してチェックし、このトレーニングセッションに必要な基礎モデルが利用可能であることを確認してください。利用可能でない場合は、[クラウドアセット管理 ](./CloudAssetsManage.md) の **Upload Models** を使って、*SD Checkpoints* カテゴリの下に基礎モデルをアップロードすることができます。

また、以下のコマンドを使って、ローカルの SD モデルを S3 バケットにアップロードすることもできます。

ローカルの SD モデルを S3 バケットにアップロードするコマンド
``` 
# 認証情報の設定
aws configure 
# ローカルの SD モデルを S3 バケットにコピー
aws s3 cp *safetensors s3://<bucket_path>/<model_path> 
``` 

### データセットの準備
データセットは、モデルの訓練と微調整には不可欠な入力です。

特定のイメージスタイルを含む LoRA モデルを訓練する例として、ユーザーは事前にイメージセットを準備する必要があります。これらのイメージは、一貫したテーマやスタイルを持ち、中程度の解像度で、数十枚あれば十分です。このイメージセットは、ベースモデルの機能に合わせて前処理する必要があります。例えば、SD ベースの LoRA モデルの訓練タスクに備えて、512x512 ピクセルにイメージをトリミングすることをお勧めします。

前処理の後は、データセットのイメージに注釈を付ける必要があります。つまり、各トレーニングイメージにテキストによる説明を追加し、対応するイメージと同じ名前のテキストファイルに保存します。イメージ注釈は、SD WebUI の組み込みイメージ注釈機能やマルチモーダル大規模モデルを使って行うことができます。モデルによる注釈は完璧ではない可能性があるため、最終的な効果を確保するためには手動での確認と調整が推奨されます。

[クラウドアセット管理 ](./CloudAssetsManage.md) の **Dataset Management** を参照して、データセットをクラウドにアップロードしてください。

また、AWSCLI コマンドを実行してデータセットを S3 バケットにアップロードすることもできます。
``` 
aws s3 sync local_folder_name s3://<bucket_name>/<folder_name> 
``` 

> **注意:** フォルダ名は数字とアンダースコアで始まる必要があります。例 : 100_demo。各イメージは、同じ名前の txt ファイルと対で存在する必要があります。例 : demo1.png, demo1.txt。demo1.txt には demo1.png のキャプションが含まれています。

### LoRA モデルの訓練
ベースモデルとデータセットがアップロードできたら、以下の手順に従ってください:
1. **Train Management** タブに移動し、**Training Instance Type** で希望の訓練インスタンスタイプを選択し、**FM Type** フィールドでこの訓練ジョブに使用するベースモデルのタイプ (Stable Diffusion 1.5 ベースまたは Stable Diffusion XL ベース)を選択します。次に、**Model** オプションを使ってこのトレーニングセッションに使用するベースモデルを選択し、**Dataset** オプションを使ってこのトレーニングセッションに依存するデータセットを選択します。
2. **config_params** の訓練パラメータを更新し、**Format config Params** をクリックして更新したパラムファイルの形式を確認・修正します。
3. **Create Training Job** をクリックして訓練ジョブを送信します。
4. **Trainings List** を更新して訓練ジョブの状況を確認します。
5. 正常に訓練した LoRA モデルは、**txt2img** や **img2img** で直接選択して、画像生成に使うことができます。詳細は [txt2img ガイド ](./txt2img-guide.md) や [img2img ガイド ](./img2img-guide.md) を参照してください。

### 訓練 API の呼び出し

[API ドキュメント ](https://awslabs.github.io/stable-diffusion-aws-extension/en/developer-guide/api/1.5.0/) を参照して、訓練 API を呼び出すことができます。
