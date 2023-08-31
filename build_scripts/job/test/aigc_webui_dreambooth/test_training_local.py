import sys 
import json

sys.path.append(".")
import sagemaker_entrypoint

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
    s3_output_path = "s3://"
    sagemaker_entrypoint.main(s3_input_path, s3_output_path, training_params)