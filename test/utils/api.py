import json
import logging

import requests
from jsonschema.validators import validate

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Api:
    schema = None

    def __init__(self, config):
        self.config = config

    def req(self,
            method: str,
            path: str,
            operation_id: str = None,
            headers=None,
            data=None,
            params=None):

        if data is not None:
            data = json.dumps(data)

        url = f"{self.config.host_url}/prod/{path}"

        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            params=params,
            timeout=(30, 40)
        )

        dump_string = ""
        if headers:
            dump_string += f"\nRequest headers: {get_json(headers)}"
        if data:
            dump_string += f"\nRequest data: {get_json(data)}"
        if params:
            dump_string += f"\nRequest params: {get_json(params)}"
        if resp.status_code:
            dump_string += f"\nResponse status_code: {resp.status_code}"
        if resp.text:
            dump_string += f"\nResponse body: {get_json(resp.text)}"

        resp.dumps = lambda: logger.info(
            f"\n----------------------------"
            f"\n{method} {url}"
            f"{dump_string}"
            f"\n----------------------------"
        )

        if operation_id:
            validate_response(self, resp, operation_id)

        return resp

    def ping(self, headers=None):
        return self.req(
            "GET",
            "ping",
            operation_id='Ping',
            headers=headers
        )

    def root(self, headers=None):
        return self.req(
            "GET",
            "",
            operation_id='RootAPI',
            headers=headers
        )

    def doc(self, headers=None):
        return self.req(
            "GET",
            "api",
            headers=headers
        )

    def delete_endpoints(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "endpoints",
            headers=headers,
            operation_id='DeleteEndpoints',
            data=data
        )

    def delete_users(self, headers=None, data=None):
        return self.req(
            "DELETE",
            f"users",
            headers=headers,
            operation_id='DeleteUsers',
            data=data
        )

    def delete_executes(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "executes",
            headers=headers,
            operation_id='DeleteExecutes',
            data=data
        )

    def delete_roles(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "roles",
            headers=headers,
            operation_id='DeleteRoles',
            data=data
        )

    def delete_datasets(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "datasets",
            headers=headers,
            operation_id='DeleteDatasets',
            data=data
        )

    def delete_trainings(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "trainings",
            headers=headers,
            operation_id='DeleteTrainings',
            data=data
        )

    def delete_inferences(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "inferences",
            headers=headers,
            operation_id='DeleteInferenceJobs',
            data=data
        )

    def delete_checkpoints(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "checkpoints",
            headers=headers,
            operation_id='DeleteCheckpoints',
            data=data
        )

    def list_roles(self, headers=None, params=None):
        return self.req(
            "GET",
            "roles",
            headers=headers,
            operation_id='ListRoles',
            params=params
        )

    def prepare(self, headers=None, data=None):
        return self.req(
            "POST",
            "prepare",
            headers=headers,
            operation_id='',
            data=data
        )

    def create_role(self, headers=None, data=None):
        return self.req(
            "POST",
            "roles",
            headers=headers,
            operation_id='CreateRole',
            data=data
        )

    def list_users(self, headers=None, params=None):
        return self.req(
            "GET",
            "users",
            headers=headers,
            operation_id='ListUsers',
            params=params
        )

    def create_user(self, headers=None, data=None):
        return self.req(
            "POST",
            "users",
            headers=headers,
            operation_id='CreateUser',
            data=data
        )

    def list_checkpoints(self, headers=None, params=None):
        return self.req(
            "GET",
            "checkpoints",
            headers=headers,
            operation_id='ListCheckpoints',
            params=params
        )

    def create_checkpoint(self, headers=None, data=None):
        return self.req(
            "POST",
            "checkpoints",
            headers=headers,
            operation_id='CreateCheckpoint',
            data=data
        )

    def update_checkpoint(self, checkpoint_id: str, headers=None, data=None):
        return self.req(
            "PUT",
            f"checkpoints/{checkpoint_id}",
            headers=headers,
            operation_id='UpdateCheckpoint',
            data=data
        )

    def list_endpoints(self, headers=None, params=None):
        return self.req(
            "GET",
            "endpoints",
            headers=headers,
            operation_id='ListEndpoints',
            params=params
        )

    def create_endpoint(self, headers=None, data=None):
        return self.req(
            "POST",
            "endpoints",
            headers=headers,
            operation_id='CreateEndpoint',
            data=data
        )

    def create_inference(self, headers=None, data=None):
        return self.req(
            "POST",
            "inferences",
            headers=headers,
            operation_id='CreateInferenceJob',
            data=data
        )

    def create_execute(self, headers=None, data=None):
        return self.req(
            "POST",
            "executes",
            headers=headers,
            operation_id='CreateExecute',
            data=data
        )

    def list_executes(self, headers=None, params=None):
        return self.req(
            "GET",
            "executes",
            headers=headers,
            operation_id='ListExecutes',
            params=params
        )

    def start_inference_job(self, job_id: str, headers=None):
        return self.req(
            "PUT",
            f"inferences/{job_id}/start",
            operation_id='StartInferences',
            headers=headers,
        )

    def get_training_job(self, job_id: str, headers=None):
        return self.req(
            "GET",
            f"trainings/{job_id}",
            operation_id='GetTraining',
            headers=headers,
        )

    def get_execute_job(self, prompt_id: str, headers=None):
        return self.req(
            "GET",
            f"executes/{prompt_id}",
            operation_id='GetExecute',
            headers=headers
        )

    def get_inference_job(self, job_id: str, headers=None):
        return self.req(
            "GET",
            f"inferences/{job_id}",
            operation_id='GetInferenceJob',
            headers=headers
        )

    def list_datasets(self, headers=None, params=None):
        return self.req(
            "GET",
            "datasets",
            headers=headers,
            operation_id='ListDatasets',
            params=params
        )

    def get_dataset(self, name: str, headers=None):
        return self.req(
            "GET",
            f"datasets/{name}",
            operation_id='GetDataset',
            headers=headers
        )

    def create_dataset(self, headers=None, data=None):
        return self.req(
            "POST",
            "datasets",
            headers=headers,
            operation_id='CreateDataset',
            data=data
        )

    def update_dataset(self, dataset_id: str, headers=None, data=None):
        return self.req(
            "PUT",
            f"datasets/{dataset_id}",
            headers=headers,
            operation_id='UpdateDataset',
            data=data
        )

    def crop_dataset(self, dataset_id: str, headers=None, data=None):
        return self.req(
            "POST",
            f"datasets/{dataset_id}/crop",
            headers=headers,
            operation_id='CropDataset',
            data=data
        )

    def create_training_job(self, headers=None, data=None):
        return self.req(
            "POST",
            "trainings",
            headers=headers,
            operation_id='CreateTraining',
            data=data
        )

    def list_trainings(self, headers=None, params=None):
        return self.req(
            "GET",
            "trainings",
            headers=headers,
            operation_id='ListTrainings',
            params=params
        )

    def list_inferences(self, headers=None, params=None):
        return self.req(
            "GET",
            "inferences",
            headers=headers,
            operation_id='ListInferences',
            params=params
        )


def get_schema_by_id_and_code(api: Api, operation_id: str, code: int):
    code = str(code)

    responses = None
    for path, methods in api.schema['paths'].items():
        for method, op in methods.items():
            if op.get('operationId') == operation_id:
                responses = op['responses']
                break

    if responses is None:
        raise Exception(f'{operation_id} not found')

    if f"{code}" not in responses:
        raise Exception(f'{code} not found in responses of {operation_id}')

    ref = responses[f"{code}"]['content']['application/json']['schema']['$ref']
    model_name = ref.split('/')[-1]
    json_schema = api.schema['components']['schemas'][model_name]

    return json_schema


def validate_response(api: Api, resp: requests.Response, operation_id: str):
    if resp.status_code != 204:
        with open(f"response.json", "w") as s:
            s.write(json.dumps(resp.json(), indent=4))

    validate_schema = get_schema_by_id_and_code(api, operation_id, resp.status_code)

    if resp.status_code == 204:
        return

    try:
        validate(instance=resp.json(), schema=validate_schema)
    except Exception as e:
        print(f"\n**********************************************")
        with open(f"schema.json", "w") as s:
            s.write(json.dumps(validate_schema, indent=4))
        print(f"\n**********************************************")
        print(operation_id)
        print(f"\n**********************************************")
        raise e


def get_json(data):
    try:
        # if data is string
        if isinstance(data, str):
            return json.dumps(json.loads(data), indent=4)
        # if data is object
        if isinstance(data, dict):
            json.dumps(dict(data), indent=4)
        return str(data)
    except TypeError:
        return str(data)
