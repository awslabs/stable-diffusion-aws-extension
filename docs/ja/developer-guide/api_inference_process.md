## API を通してのインファレンス方法

- `CreateEndpoint`を使ってエンドポイントを作成する
- `CreateCheckpoint`を使ってモデルファイルをアップロードする。`API Upload Checkpoint Process`を参照してください。
- `非同期インファレンス`または`リアルタイムインファレンス`を選択する

### 非同期インファレンス
- `CreateInferenceJob`を使ってインファレンスジョブを作成する
- `CreatInferenceJob`で返された事前署名アドレス`api_params_s3_upload_url`に基づいてインファレンスパラメータをアップロードする
- `StartInferenceJob`を使ってインファレンスジョブを開始する
- `GetInferenceJob`を使ってインファレンスジョブを取得し、ステータスを確認し、成功した場合はリクエストを停止する

### リアルタイムインファレンス
- `CreateInferenceJob`を使ってインファレンスジョブを作成する
- `CreatInferenceJob`で返された事前署名アドレス`api_params_s3_upload_url`に基づいてインファレンスパラメータをアップロードする
- `StartInferenceJob`を使ってインファレンスジョブを開始する。リアルタイムインファレンスジョブはこのインターフェイスでインファレンス結果を取得する
