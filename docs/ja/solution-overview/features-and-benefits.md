## 機能
 
このソリューションは、Stable Diffusion WebUI の以下のネイティブ機能/サードパーティ拡張機能のクラウドベースのオペレーションをサポートしています:

| **機能** | **サポートバージョン** | **注意事項** | 
| ------------- | ------------- | ------------- | 
| [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | V1.8.0 | 公式のサンプラーである LCM、SDXL-Inpaint などをサポート |
| [img2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | V1.8.0 | バッチ処理を除くすべての機能をサポート |
| [txt2img](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | V1.8.0 | | 
| [LoRa](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | V1.2.1 | | 
| [ControlNet](https://github.com/Mikubill/sd-webui-controlnet) | V1.1.410 | SDXL + ControlNet 推論をサポート |
| [Tiled Diffusion & VAE](https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git) | f9f8073e64f4e682838f255215039ba7884553bf | 
| [ReActor for Stable Diffusion](https://github.com/Gourieff/sd-webui-reactor) | 0.6.1 | 
| [Extras](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | V1.8.0 | API | 
| [rembg](https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git) | 3d9eedbbf0d585207f97d5b21e42f32c0042df70 | API | 
| [kohya_ss](https://github.com/bmaltais/kohya_ss) | | 

## 利点

* **簡単なインストール**: このソリューションは CloudFormation を活用して AWS ミドルウェアを簡単にデプロイできます。ネイティブの Stable Diffusion WebUI (WebUI) 機能とサードパーティ拡張機能のインストールと併せて、ユーザーは Amazon SageMaker のクラウドリソースを推論、トレーニング、微調整タスクに迅速に活用できます。

* **コミュニティネイティブ**: このソリューションは拡張機能として実装されているため、ユーザーは変更を加えずに既存の WebUI を継続して使用できます。さらに、このソリューションのコードはオープンソースで、非侵襲的なデザインに従っているため、ユーザーは ControlNet や LoRa などの人気プラグインなど、コミュニティ関連の機能の反復に追随できます。

* **高スケーラビリティ**: このソリューションは WebUI インターフェースとバックエンドを分離することで、WebUI が GPU の制限なしにサポートされるターミナルで起動できるようにしています。既存のトレーニング、推論、その他のタスクを提供された拡張機能機能を通じて Amazon SageMaker に移行できるため、ユーザーは弾力的なコンピューティングリソース、コスト削減、柔軟性、スケーラビリティを享受できます。
