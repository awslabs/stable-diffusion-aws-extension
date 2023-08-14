import sys 
import json
import os

sys.path.append("extensions/stable-diffusion-aws-extension")
from build_scripts.training import sagemaker_entrypoint

db_config_path = "models/sagemaker_dreambooth/test-1/db_config_cloud.json"
os.system(f"cp db_config_cloud.json {db_config_path}")
os.system(f"tar cvf db_config.tar {db_config_path}")
sys.path.insert(0, os.path.join(os.getcwd(), "extensions/stable-diffusion-aws-extension/"))
from utils import upload_file_to_s3
upload_file_to_s3("db_config.tar", "stable-diffusion-aws-extension-aigcbucket-test", directory="Stable-diffusion/train/test-1/input", object_name=None)

if __name__ == "__main__":
    args_json_file_path = sys.argv[1]
    with open(args_json_file_path) as args_json_file:
        args = json.load(args_json_file)
    training_params = {
        "training_params": {
            "model_name": args["model_name"],
            "model_type": args["model_type"],
            "s3_model_path": args["s3_model_path"],
            "data_tar_list": args["data_tar_list"],
            "class_data_tar_list": args["class_data_tar_list"],
        }
    }
    s3_input_path = args["input_location"]
    s3_output_path = "s3://stable-diffusion-aws-extension-aigcbucket-test/Stable-diffusion/train/test-1/output/"
    sagemaker_entrypoint.main(s3_input_path, s3_output_path, training_params)