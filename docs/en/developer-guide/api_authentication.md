## Security Authentication

All APIs use API keys for security verification, and all API requests should include your API key in the HTTP header. The `x-api-key` is as follows:
```Config
X-api-key: xxxxxxxxxxxxxxxxxxxx
```

## User Authentication

Please include `username` in the HTTP header. For example, if the username configured on WebUI is `admin`, then:

```config
username: admin
```

## Version 1.4.0 or earlier

Your `Authorization` should be included in the HTTP header as follows:

```Config
Authorization: Bearer {TOKEN}
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
