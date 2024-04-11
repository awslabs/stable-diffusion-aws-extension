### URL からのアップロード
- `CreateCheckpoint` リクエスト

### ファイルからのアップロード
- モデルファイルを作成するために `CreateCheckpoint` リクエストを行う
- S3 の事前署名付きアドレスを通じてファイルをアップロードする
- `UpdateCheckpoint` を通じてステータスを更新する
