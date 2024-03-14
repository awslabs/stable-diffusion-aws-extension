
## training_params

|Name|Details|Example|
|--|--|--|
|training_instance_type| The instance type used for Kohya training | ml.g5.4xlarge, ml.g4dn.2xlarge | 
|fm_type| Foundation model type, sd_xl for training based on SDXL model, sd_1_5 for training based on SD 1.5 model | sd_xl, sd_1_5 |
|s3_model_path|SD model path, it is an S3 path|s3://demo/Stable-diffusion/checkpoint/custom/05de5ff6-409d-4fd5-a59a-5c58f8fb2d04/v1-5-pruned-emaonly.safetensors |
|s3_data_path|Dataset path, it is an S3 path|s3://demo/dataset/example_ds|

## config_params

|Name|Details|Example|
|--|--|--|
|output_name|Model output name|model_output |
|epoch|The number of times your model will iterate over the entire training dataset|20|
|max_train_epochs|Enforce number of epoch| 50 |
|learning_rate|how quickly the model adapts during training|0.000001|
||||
||||
||||
||||
||||
||||
||||
||||
||||






{
  "LoRA_type": "LyCORIS/LoKr",
  "LyCORIS_preset": "full",
  "adaptive_noise_scale": 0,
  "additional_parameters": "",
  "block_alphas": "",
  "block_dims": "",
  "block_lr_zero_threshold": "",
  "bucket_no_upscale": true,
  "bucket_reso_steps": 64,
  "cache_latents": true,
  "cache_latents_to_disk": true,
  "caption_dropout_every_n_epochs": 0.0,
  "caption_dropout_rate": 0,
  "caption_extension": ".txt",
  "clip_skip": "1",
  "color_aug": false,
  "constrain": 0.0,
  "conv_alpha": 64,
  "conv_block_alphas": "",
  "conv_block_dims": "",
  "conv_dim": 64,
  "debiased_estimation_loss": false,
  "decompose_both": false,
  "dim_from_weights": false,
  "down_lr_weight": "",
  "enable_bucket": true,
  "epoch": 20, ---
  "factor": -1,
  "flip_aug": false,
  "fp8_base": false,
  "full_bf16": false,
  "gradient_accumulation_steps": 1,
  "gradient_checkpointing": true,
  "keep_tokens": "0",
  "learning_rate": 1.0,
  "logging_dir": "/folder/logging/folder",
  "lora_network_weights": "",
  "lr_scheduler": "constant",
  "lr_scheduler_args": "",
  "lr_scheduler_num_cycles": "",
  "lr_scheduler_power": "",
  "lr_warmup": 0,
  "max_bucket_reso": 2048,
  "max_data_loader_n_workers": "0",
  "max_grad_norm": 1,
  "max_resolution": "1024,1024",
  "max_timestep": 1000,
  "max_token_length": "75",
  "max_train_epochs": "", --
  "max_train_steps": "",
  "mem_eff_attn": false,
  "mid_lr_weight": "",
  "min_bucket_reso": 256,
  "min_snr_gamma": 10,
  "min_timestep": 0,
  "mixed_precision": "bf16",
  "model_list": "custom",
  "module_dropout": 0.1,
  "multires_noise_discount": 0.2,
  "multires_noise_iterations": 8,
  "network_alpha": 64,
  "network_dim": 64,
  "network_dropout": 0,
  "no_token_padding": false,
  "noise_offset": 0.0357,
  "noise_offset_type": "Multires",
  "num_cpu_threads_per_process": 2,
  "optimizer": "Prodigy",
  "optimizer_args": "",
  "output_dir": "/folder/output/folder",
  "output_name": "folder_model_output_name", ---
  "persistent_data_loader_workers": false,
  "pretrained_model_name_or_path": "stabilityai/stable-diffusion-xl-base-1.0",
  "prior_loss_weight": 1.0,
  "random_crop": false,
  "rank_dropout": 0.1,
  "rank_dropout_scale": false,
  "reg_data_dir": "/folder/regularisation/folder",
  "rescaled": false,
  "resume": "",
  "sample_every_n_epochs": 1,
  "sample_every_n_steps": 1,
  "sample_prompts": "sample prompts",
  "sample_sampler": "euler_a",
  "save_every_n_epochs": 1,
  "save_every_n_steps": 0,
  "save_last_n_steps": 0,
  "save_last_n_steps_state": 0,
  "save_model_as": "safetensors",
  "save_precision": "fp16",
  "save_state": false,
  "scale_v_pred_loss_like_noise_pred": false,
  "scale_weight_norms": 0,
  "sdxl": true,
  "sdxl_cache_text_encoder_outputs": false,
  "sdxl_no_half_vae": true,
  "seed": "12345",
  "shuffle_caption": false,
  "stop_text_encoder_training": 0,
  "text_encoder_lr": 1.0,
  "train_batch_size": 8,
  "train_data_dir": "/folder/image/folder",
  "train_norm": false,
  "train_on_input": true,
  "training_comment": "",
  "unet_lr": 1.0,
  "unit": 1,
  "up_lr_weight": "",
  "use_cp": true,
  "use_scalar": false,
  "use_tucker": false,
  "use_wandb": false,
  "v2": false,
  "v_parameterization": false,
  "v_pred_like_loss": 0,
  "vae": "",
  "vae_batch_size": 0,
  "wandb_api_key": "",
  "weighted_captions": false,
  "xformers": "xformers"
}

{
  "LoRA_type": "LyCORIS/LoKr",
  "LyCORIS_preset": "full",
  "adaptive_noise_scale": 0,
  "additional_parameters": "",
  "block_alphas": "",
  "block_dims": "",
  "block_lr_zero_threshold": "",
  "bucket_no_upscale": true,
  "bucket_reso_steps": 64,
  "cache_latents": true,
  "cache_latents_to_disk": true,
  "caption_dropout_every_n_epochs": 0.0,
  "caption_dropout_rate": 0,
  "caption_extension": ".txt",
  "clip_skip": "1",
  "color_aug": false,
  "constrain": 0.0,
  "conv_alpha": 64,
  "conv_block_alphas": "",
  "conv_block_dims": "",
  "conv_dim": 64,
  "debiased_estimation_loss": false,
  "decompose_both": false,
  "dim_from_weights": false,
  "down_lr_weight": "",
  "enable_bucket": true,
  "epoch": 20,
  "factor": -1,
  "flip_aug": false,
  "fp8_base": false,
  "full_bf16": false,
  "gradient_accumulation_steps": 1,
  "gradient_checkpointing": true,
  "keep_tokens": "0",
  "learning_rate": 1.0,
  "logging_dir": "/folder/logging/folder",
  "lora_network_weights": "",
  "lr_scheduler": "constant",
  "lr_scheduler_args": "",
  "lr_scheduler_num_cycles": "",
  "lr_scheduler_power": "",
  "lr_warmup": 0,
  "max_bucket_reso": 2048,
  "max_data_loader_n_workers": "0",
  "max_grad_norm": 1,
  "max_resolution": "1024,1024",
  "max_timestep": 1000,
  "max_token_length": "75",
  "max_train_epochs": "",
  "max_train_steps": "",
  "mem_eff_attn": false,
  "mid_lr_weight": "",
  "min_bucket_reso": 256,
  "min_snr_gamma": 10,
  "min_timestep": 0,
  "mixed_precision": "bf16",
  "model_list": "custom",
  "module_dropout": 0.1,
  "multires_noise_discount": 0.2,
  "multires_noise_iterations": 8,
  "network_alpha": 64,
  "network_dim": 64,
  "network_dropout": 0,
  "no_token_padding": false,
  "noise_offset": 0.0357,
  "noise_offset_type": "Multires",
  "num_cpu_threads_per_process": 2,
  "optimizer": "Prodigy",
  "optimizer_args": "",
  "output_dir": "/folder/output/folder",
  "output_name": "folder_model_output_name",
  "persistent_data_loader_workers": false,
  "pretrained_model_name_or_path": "stabilityai/stable-diffusion-xl-base-1.0",
  "prior_loss_weight": 1.0,
  "random_crop": false,
  "rank_dropout": 0.1,
  "rank_dropout_scale": false,
  "reg_data_dir": "/folder/regularisation/folder",
  "rescaled": false,
  "resume": "",
  "sample_every_n_epochs": 1,
  "sample_every_n_steps": 1,
  "sample_prompts": "sample prompts",
  "sample_sampler": "euler_a",
  "save_every_n_epochs": 1,
  "save_every_n_steps": 0,
  "save_last_n_steps": 0,
  "save_last_n_steps_state": 0,
  "save_model_as": "safetensors",
  "save_precision": "fp16",
  "save_state": false,
  "scale_v_pred_loss_like_noise_pred": false,
  "scale_weight_norms": 0,
  "sdxl": true,
  "sdxl_cache_text_encoder_outputs": false,
  "sdxl_no_half_vae": true,
  "seed": "12345",
  "shuffle_caption": false,
  "stop_text_encoder_training": 0,
  "text_encoder_lr": 1.0,
  "train_batch_size": 8,
  "train_data_dir": "/folder/image/folder",
  "train_norm": false,
  "train_on_input": true,
  "training_comment": "",
  "unet_lr": 1.0,
  "unit": 1,
  "up_lr_weight": "",
  "use_cp": true,
  "use_scalar": false,
  "use_tucker": false,
  "use_wandb": false,
  "v2": false,
  "v_parameterization": false,
  "v_pred_like_loss": 0,
  "vae": "",
  "vae_batch_size": 0,
  "wandb_api_key": "",
  "weighted_captions": false,
  "xformers": "xformers"
}






## Overview

By passing a configuration file using `--dataset_config`, users can fine-tune specific settings.

* Multiple datasets can be configured:
    * For example, you can set different `resolution` values for each dataset and combine them for training.
    * If you're using both DreamBooth and fine-tuning methods, you can mix datasets from both approaches.
* Settings can be adjusted for each subset:
    * Subsets are created by dividing the dataset based on image directories or metadata.
    * Options like `keep_tokens` and `flip_aug` can be set separately for each subset. On the other hand, options like `resolution` and `batch_size` can be set for the entire dataset, with common values for subsets within the same dataset. More details are explained below.

The configuration file format can be either JSON or TOML. For ease of writing, we recommend using [TOML](https://toml.io/ja/v1.0.0-rc.2). Below, we'll explain using TOML as the assumed format.

Here's an example of a configuration file written in TOML:

```toml
[general]
shuffle_caption = true
caption_extension = '.txt'
keep_tokens = 1

# This is a DreamBooth-style dataset
[[datasets]]
resolution = 512
batch_size = 4
keep_tokens = 2

  [[datasets.subsets]]
  image_dir = 'C:\hoge'
  class_tokens = 'hoge girl'
  # This subset uses keep_tokens = 2 (values from the parent dataset)

  [[datasets.subsets]]
  image_dir = 'C:\fuga'
  class_tokens = 'fuga boy'
  keep_tokens = 3

  [[datasets.subsets]]
  is_reg = true
  image_dir = 'C:\reg'
  class_tokens = 'human'
  keep_tokens = 1

# This is a fine-tuning-style dataset
[[datasets]]
resolution = [768, 768]
batch_size = 2

  [[datasets.subsets]]
  image_dir = 'C:\piyo'
  metadata_file = 'C:\piyo\piyo_md.json'
  # This subset uses keep_tokens = 1 (values from the general section)
```

In this example, three directories are used for the DreamBooth-style dataset (512x512 with batch size 4), and one directory is used for the fine-tuning-style dataset (768x768 with batch size 2).

## Configuration for Datasets and Subsets

Settings related to datasets and subsets are divided into several sections:

* `[general]`
    * Specifies options that apply to all datasets or subsets.
    * If the same option exists in both dataset-specific and subset-specific settings, the latter takes precedence.
* `[[datasets]]`
    * This is where you register dataset-specific settings.
---

Feel free to ask if you need further clarification or have additional questions! 😊.

Source: Conversation with Bing, 3/11/2024
(1) Translate Markdown file from Japanese to English - GroupDocs. https://products.groupdocs.app/translation/markdown/japanese-english.
(2) How To Change The Language On Your Japanese Notepad To English. https://whatismarkdown.com/how-to-change-the-language-on-your-japanese-notepad-to-english/.
(3) Translate any document from Japanese to English - GroupDocs. https://products.groupdocs.app/translation/total/japanese-english.
(4) Translate from Japanese to English - NeuralWriter. https://neuralwriter.com/translate-tool/ja-en/.
(5) en.wikipedia.org. https://en.wikipedia.org/wiki/Markdown.