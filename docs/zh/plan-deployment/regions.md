截至2023年06月，本解决方案支持部署在以下亚马逊云科技区域：




- 美国东部（弗吉尼亚北部）区域:   us-east-1
- 美国东部（俄亥俄）区域:   us-east-2
- 美国西部（加利福尼亚北部）区域:   us-west-1
- 美国西部（俄勒冈）区域:   us-west-2
- 南美洲（圣保罗）区域:   sa-east-1
- 欧洲（爱尔兰）区域:   eu-west-1
- 欧洲（伦敦）区域:   eu-west-2
- 欧洲（巴黎）区域:   eu-west-3
- 欧洲（米兰）区域:   eu-north-1
- 欧洲（法兰克福）区域:   eu-central-1
- 加拿大（中部）区域:   ca-central-1
- 亚太地区（东京）区域:   ap-northeast-1
- 亚太地区（首尔）区域:   ap-northeast-2
- 亚太区域（大阪）区域:   ap-northeast-3
- 亚太地区（新加坡）区域:   ap-southeast-1
- 亚太地区（悉尼）区域:   ap-southeast-2
- 亚太地区（孟买）区域:   ap-south-1
- 亚太地区（香港）区域:   ap-east-1


!!!Important "注意"
    近日，我们在测试中发现，在美国东部（俄亥俄）区域(us-east-2)、美国西部（加利福尼亚北部）区域(us-west-1)、美国西部（俄勒冈）区域(us-west-2)新创建的Amazon S3桶中遇到了CORS问题会导致用户无法通过浏览器上传配置文件。尽管更新了CORS配置，用户在使用预签名URL上传文件时仍经常在浏览器中遇到CORS问题。问题在大约两小时后自行解决，我们正在和Amazon S3 Service team沟通此问题， 基于此，建议用户首选在美国东部（弗吉尼亚北部）区域(us-east-1)/亚太地区（东京）区域(ap-northeast-1)/亚太地区（新加坡）区域(ap-southeast-1)部署。

                