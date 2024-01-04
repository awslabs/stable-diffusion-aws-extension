from transformers import BertTokenizerFast, CLIPTextModel, CLIPTokenizer, CLIPVisionConfig

tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")
text_model = CLIPTextModel.from_pretrained("openai/clip-vit-large-patch14")
config = CLIPVisionConfig.from_pretrained("openai/clip-vit-large-patch14")
tokenizer2 = BertTokenizerFast.from_pretrained("bert-base-uncased")
