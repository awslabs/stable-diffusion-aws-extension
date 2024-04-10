以下は、Extension for Stable Diffusion on AWS を使用する際に遭遇する可能性のあるエラーや問題を修正する方法です。

**エラー : 'RuntimeError: "LayerNormKernelImpl" not implemented for 'Half'' というエラーメッセージが表示される** 

このエラーは webUI フロントエンドをデプロイする際に発生します。webUI を起動する際に `--precision full --no-half` オプションを追加することをお勧めします。

``` 
./webui.sh --skip-torch-cuda-test --precision full --no-half 
``` 


**エラー : Ubuntu で `python3 -m venv env` を使って Python venv をインストールできない** 

このエラーは、システムのデフォルトが Python 3.9 で、Ubuntu 20.04 は Python 3.8 の場合に発生します。ユーザーは `sudo apt install python3.8-venv` を使って Python の完全なバージョンを明示的に指定してインストールすることができます。


**エラー : webUI を使用中、右上にエラーが表示される** 

これは接続エラーの可能性があり、オープンソースの webUI プロジェクトがクラッシュした可能性があります。手動で webUI を再起動することで解決できます。**Restart webUI** ボタンを使ってマニュアルで再起動することをお勧めします。

![Restart webUI](./images/restart_UI.png) 

