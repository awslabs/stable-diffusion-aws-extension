
## セキュリティ認証

すべての API では API キーによるセキュリティ検証が行われ、すべての API 要求に API キーを HTTP ヘッダーに含める必要があります。`x-api-key` は以下の通りです:

```Config 
X-api-key: xxxxxxxxxxxxxxxxxxxx 
``` 

## ユーザー認証

HTTP ヘッダーに `username` を含めてください。例えば、WebUI で設定されているユーザー名が `admin` の場合は以下のようになります:

```config 
username: admin 
``` 

> API がデプロイされると、`api` というユーザーが組み込まれています。WebUI で初期化しない場合や、API でユーザーを新規作成しない場合は、`api` をユーザー名として使用できます。

## バージョン 1.4.0 以前

`Authorization` は HTTP ヘッダーに以下のように含める必要があります:

```Config 
Authorization: Bearer {TOKEN} 
``` 

トークンアルゴリズム (Python の例 ): 

```Python 
import base64 
Username="WebUI のユーザー名"
Token=base64.b16encode (username.encode ("utf-8")).decode ("utf-8") 
``` 

例えば、WebUI で設定されているユーザー名が `admin` の場合は以下のようになります:
```Config 
Authorization: Bearer 61646D696E 
``` 
