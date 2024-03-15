**安全验证**

所有 API 使用 API 密钥进行安全验证，所有 API 请求都应在 HTTP 标头中包含您的 API 密钥，`x-api-key` 如下所示：

```config
x-api-key: xxxxxxxxxxxxxxxxxxxx
```

**用户验证**

> 注意：用户验证将在下一个版本中移除。

部分 API 除了要使用 `x-api-key` 作为基本的安全验证外，还需要进行用户验证。应在 HTTP 标头中包含您的 `Authorization` 如下所示：

```config
Authorization: Bearer YOUR_TOKEN
```

Token 算法（Python 示例）：

```python
import base64

username = "your username on webui"
token = base64.b16encode(username.encode("utf-8")).decode("utf-8")
```

例如，如果在 WebUI 上配置的用户名是 `admin`，则：

```config
Authorization: Bearer 61646D696E
```
