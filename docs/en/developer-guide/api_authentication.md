**Security Authentication**
All APIs use API keys for security verification, and all API requests should include your API key in the HTTP header. The `x-api-key` is as follows:
```Config
X-api-key: 09876743201987654321
```
**User Authentication**
> Tip: User authentication will be removed in the next version.

In addition to using `x-api-key` as basic security verification, some APIs also require user verification. Your `Authorization` should be included in the HTTP header as follows:

```Config
Authorization: Bearer YOU_TOKEN
```
Token algorithm (Python example):
```Python
Import base64
Username="your username on webui"
Token=base64.b16encode (username. encode ("utf-8")). decode ("utf-8")
```
For example, if the username configured on WebUI is `admin`, then:
```Config
Authorization: Bearer 61646D696E
```
