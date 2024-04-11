
# Comfy 

# 実行

<a id="opIdCreateInferenceJob"></a>

## GET 実行の詳細を取得する GetExecute 

 GET /executes/prompt_id 

### パラメータ

|名前|場所|種類|必須|説明|
|---|---|---|---|---|
|prompt_id|クエリ|string|はい|prompt の ID|

> レスポンスサンプル

> 成功

```json 
{
  "statusCode": 200,
  "debug": {
    "function_url": "https://ap-northeast-1.console.aws.amazon.com/lambda/home?region=ap-northeast-1#/functions/Extension-for-Stable-Diff-GetExecutelambda150CA75A-OnCA61VlLPFO",
    "log_url": "https://ap-northeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-1#logsV2:log-groups/log-group/%2Faws%2Flambda%2FExtension-for-Stable-Diff-GetExecutelambda150CA75A-OnCA61VlLPFO/log-events/2024%2F03%2F31%2F%5B%24LATEST%5D42a5a96838004138bd6cdaab65aa0904",
    "trace_url": "https://ap-northeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-1#xray:traces/1-66094ccd-59bee192247987145ec3f20e"
  },
  "data": {
    "prompt_id": "11111111-1111-1112",
    "need_sync": true,
    "sagemaker_raw": {},
    "prompt_path": "",
    "endpoint_name": "esd-async-test",
    "status": "created",
    "create_time": "2024-03-31T11:25:21.493741",
    "inference_type": "Async",
    "start_time": "2024-03-31T11:25:21.493756",
    "prompt_params": {
      "prompt": {
        "4": {
          "inputs": {
            "ckpt_name": "sdXL_v10VAEFix.safetensors"
          },
          "class_type": "CheckpointLoaderSimple"
        },
        "5": {
          "inputs": {
            "width": "1024",
            "height": "1024",
            "batch_size": "1"
          },
          "class_type": "EmptyLatentImage"
        },
        "6": {
          "inputs": {
            "clip": [
              "4",
              "1"
            ],
            "text": "evening sunset scenery blue sky nature, glass bottle with a galaxy in it"
          },
          "class_type": "CLIPTextEncode"
        },
        "7": {
          "inputs": {
            "clip": [
              "4",
              "1"
            ],
            "text": "text, watermark"
          },
          "class_type": "CLIPTextEncode"
        },
        "10": {
          "inputs": {
            "latent_image": [
              "5",
              "0"
            ],
            "cfg": "8",
            "return_with_leftover_noise": "enable",
            "end_at_step": "20",
            "positive": [
              "6",
              "0"
            ],
            "add_noise": "enable",
            "steps": "25",
            "scheduler": "normal",
            "negative": [
              "7",
              "0"
            ],
            "start_at_step": "0",
            "sampler_name": "euler",
            "noise_seed": "721897303308196",
            "model": [
              "4",
              "0"
            ]
          },
          "class_type": "KSamplerAdvanced"
        },
        "11": {
          "inputs": {
            "latent_image": [
              "10",
              "0"
            ],
            "cfg": "8",
            "return_with_leftover_noise": "disable",
            "end_at_step": "10000",
            "positive": [
              "15",
              "0"
            ],
            "add_noise": "disable",
            "steps": "25",
            "scheduler": "normal",
            "negative": [
              "16",
              "0"
            ],
            "start_at_step": "20",
            "sampler_name": "euler",
            "noise_seed": "0",
            "model": [
              "12",
              "0"
            ]
          },
          "class_type": "KSamplerAdvanced"
        },
        "12": {
          "inputs": {
            "ckpt_name": "sdXL_v10VAEFix.safetensors"
          },
          "class_type": "CheckpointLoaderSimple"
        },
        "15": {
          "inputs": {
            "clip": [
              "12",
              "1"
            ],
            "text": "evening sunset scenery blue sky nature, glass bottle with a galaxy in it"
          },
          "class_type": "CLIPTextEncode"
        },
        "16": {
          "inputs": {
            "clip": [
              "12",
              "1"
            ],
            "text": "text, watermark"
          },
          "class_type": "CLIPTextEncode"
        },
        "17": {
          "inputs": {
            "samples": [
              "11",
              "0"
            ],
            "vae": [
              "12",
              "2"
            ]
          },
          "class_type": "VAEDecode"
        },
        "19": {
          "inputs": {
            "filename_prefix": "ComfyUI",
            "images": [
              "17",
              "0"
            ]
          },
          "class_type": "SaveImage"
        }
      }
    },
    "output_path": ""
  },
  "message": "OK"
}
```

### レスポンス

|HTTP ステータスコード|意味|説明|データスキーマ|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|インライン|

### レスポンスデータスキーマ

 HTTP ステータスコード **200**

|名称|型|必須|制約|タイトル|説明|
|---|---|---|---|---|---|
|» statusCode|整数|はい|なし||なし|
|» data|オブジェクト|はい|なし||なし|
|»» inference|オブジェクト|はい|なし||なし|
|»»» id|文字列|はい|なし||なし|
|»»» type|文字列|はい|なし||なし|
|»»» api_params_s3_location|文字列|はい|なし||なし|
|»»» api_params_s3_upload_url|文字列|はい|なし||なし|
|»»» models|[オブジェクト]|はい|なし||なし|
|»»»» id|文字列|はい|なし||なし|
|»»»» name|[文字列]|はい|なし||なし|
|»»»» type|文字列|はい|なし||なし|
|» message|文字列|はい|なし||なし|

# データスキーマ

