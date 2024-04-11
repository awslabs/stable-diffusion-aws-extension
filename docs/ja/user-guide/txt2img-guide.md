# txt2img ガイド

**txt2img** タブを開くと、txt2img の ネイティブ領域と新しく追加された "Amazon SageMaker Inference" パネルの機能を組み合わせて、テキストから画像への推論を行うことができます。これにより、txt2img の推論タスクにクラウドリソースを呼び出すことができます。

## txt2img ユーザーガイド

### 一般的な推論シナリオ

1. **txt2img** タブに移動し、**Amazon SageMaker Inference** パネルを見つけます。 
![Sagemaker Inference 面板 ](../images/txt2img-inference.png) 
2. 推論に必要なパラメーターを入力します。ローカルでの推論と同様に、モデル名 (Stable Diffusion チェックポイント、Extra Networks:Lora、Hypernetworks、Textural Inversion、VAE)、プロンプト、ネガティブプロンプト、サンプリングパラメーター、推論パラメーターなど、ネイティブの **txt2img** の推論パラメーターをカスタマイズできます。VAE モデルの切り替えは、**設定** タブに移動し、左側のパネルで **Stable Diffusion** を選択し、**SD VAE** で VAE モデルを選択します (VAE モデル : Automatic = チェックポイントと同じ名前のものを使用 ; None = チェックポイントから VAE を使用)。
![Settings 面板 ](../images/setting-vae.png) 

    !!!Important 注意 
        推論で使用されるモデルファイルは、生成前にクラウドにアップロードされている必要があります。これについては、**クラウドアセット管理** の章の説明を参照してください。現在のモデルリストには、ローカルおよびクラウドベースのモデルのオプションが表示されています。クラウドベースの推論の場合、**sagemaker** というキーワードが付いたものを選択することをお勧めします。これは、それらがクラウド上にアップロードされていることを示しています。

3. **クラウド上で使用される Stable Diffusion チェックポイントモデル** を選択し、**Generate** ボタンは **Generate on Cloud** に変わります。
![Generate button 面板 ](../images/txt2img-generate-button.png) 

    !!!Important 注意 
        このフィールドは必須です。 

4. すべてのパラメーターを設定したら、**Generate on Cloud** をクリックします。

5. 推論結果を確認します。**Inference Job** ドロップダウンリストの最上位のオプションを選択すると、**txt2img** タブの右上の **Output** セクションに、推論完了時の結果が表示されます。これには、生成された画像、プロンプト、推論パラメーターが含まれています。これに基づいて、**保存** や **img2img に送信** などの後続のワークフローを実行できます。
> **注意:** リストは推論時間の逆順に並べられており、最新の推論タスクが上部に表示されます。各レコードは*推論時間 -> 推論 ID* の形式で名付けられています。

![generate results](../images/generate-results.png) 


### 連続推論シナリオ
1. **一般的な推論シナリオ** に従って、パラメーターを入力し、**Generate on Cloud** をクリックして初回の推論タスクを送信します。
2. 右側の "Output" セクションに新しい **Inference ID** が表示されるのを待ちます。
3. 新しい **Inference ID** が表示されたら、**Generate on Cloud** をもう一度クリックして次の推論タスクを実行できます。

![generate results](../images/continue-inference.png) 



### Lora などの追加モデルを使用した推論
1. WebUI のネイティブバージョンに従い、必要なモデル (Textual Inversion、Hypernetworks、Checkpoints、Lora モデルなど)のコピーをローカルマシンにアップロードします。
2. [ モデルのアップロード ](../CloudAssetsManage/) に従って、対応するモデルをクラウドにアップロードします。
3. 必要なモデルを選択し、プロンプトフィールドでモデルの重みを調整し、**Generate on Cloud** をクリックして画像を推論します。


## 推論ジョブの履歴
デフォルトでは、最新の 10 件の推論ジョブが表示されます。命名形式は Time-Type-Status-UUID です。**Show All** をチェックすると、アカウントが持つすべての推論ジョブが表示されます。**Advanced Inference Job filter** をチェックし、必要に応じてフィルターを適用すると、ユーザーがカスタマイズした推論ジョブのリストが表示されます。
