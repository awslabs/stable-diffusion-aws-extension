import base64
import logging

import gradio as gr
import requests

from aws_extension.auth_service.simple_cloud_auth import cloud_auth_manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client_api_version = "1.4.0"


def upgrade_info(resp):
    if 'x-api-version' not in resp.headers:
        gr.Warning(f"Client api version {client_api_version} is not compatible api version. "
                   f"Please update the client or api.")
        return

    api_version = resp.headers['x-api-version']

    if api_version < client_api_version:
        gr.Warning(f"extension version {client_api_version} is not compatible api version {api_version}. "
                   f"Please update the api.")
        return

    if api_version > client_api_version:
        gr.Warning(f"extension version {client_api_version} is not compatible api version {api_version}. "
                   f"Please update the extension.")
        return


class Api:
    username = None

    def set_username(self, username):
        self.username = username
        return self.username

    def __init__(self, debug: bool = True):
        self.host_url = cloud_auth_manager.api_url
        self.api_key = cloud_auth_manager.api_key
        self.debug = debug

    def req(self, method: str, path: str, headers=None, data=None, params=None):

        url = f"{self.host_url}{path}"

        if headers is None:
            headers = {
                'x-api-key': self.api_key,
                'Content-Type': 'application/json',
            }
        else:
            headers['x-api-key'] = self.api_key
            headers['Content-Type'] = 'application/json'

        if self.username:
            headers['Authorization'] = f'Bearer {base64.b16encode(self.username.encode("utf-8")).decode("utf-8")}'

        if self.debug:
            logger.info(f"{method} {url}")

            if headers:
                logger.info(f"headers: {headers}")

            if data:
                logger.info(f"data: {data}")

            if params:
                logger.info(f"params: {params}")

        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            params=params,
            timeout=(20, 30)
        )

        upgrade_info(resp)

        if self.debug:
            logger.info(f"resp headers: {resp.headers}")
            logger.info(f"{resp.status_code} {resp.text}")

        return resp

    def ping(self, headers=None):
        return self.req(
            "GET",
            "ping",
            headers=headers
        )

    def list_roles(self, headers=None, params=None):
        return self.req(
            "GET",
            "roles",
            headers=headers,
            params=params
        )

    def delete_roles(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "roles",
            headers=headers,
            data=data
        )

    def delete_datasets(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "datasets",
            headers=headers,
            data=data
        )

    def delete_models(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "models",
            headers=headers,
            data=data
        )

    def delete_trainings(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "trainings",
            headers=headers,
            data=data
        )

    def delete_inferences(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "inferences",
            headers=headers,
            data=data
        )

    def delete_checkpoints(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "checkpoints",
            headers=headers,
            data=data
        )

    def create_role(self, headers=None, data=None):
        return self.req(
            "POST",
            "roles",
            headers=headers,
            data=data
        )

    def list_users(self, headers=None, params=None):
        return self.req(
            "GET",
            "users",
            headers=headers,
            params=params
        )

    def delete_users(self, headers=None, data=None):
        return self.req(
            "DELETE",
            f"users",
            headers=headers,
            data=data
        )

    def create_user(self, headers=None, data=None):
        return self.req(
            "POST",
            "users",
            headers=headers,
            data=data
        )

    def list_checkpoints(self, headers=None, params=None):
        return self.req(
            "GET",
            "checkpoints",
            headers=headers,
            params=params
        )

    def create_checkpoint(self, headers=None, data=None):
        return self.req(
            "POST",
            "checkpoints",
            headers=headers,
            data=data
        )

    def update_checkpoint(self, checkpoint_id: str, headers=None, data=None):
        return self.req(
            "PUT",
            f"checkpoints/{checkpoint_id}",
            headers=headers,
            data=data
        )

    def delete_endpoints(self, headers=None, data=None):
        return self.req(
            "DELETE",
            "endpoints",
            headers=headers,
            data=data
        )

    def list_endpoints(self, headers=None, params=None):
        return self.req(
            "GET",
            "endpoints",
            headers=headers,
            params=params
        )

    def create_endpoint(self, headers=None, data=None):
        return self.req(
            "POST",
            "endpoints",
            headers=headers,
            data=data
        )

    def create_inference(self, headers=None, data=None):
        return self.req(
            "POST",
            "inferences",
            headers=headers,
            data=data
        )

    def start_inference_job(self, job_id: str, headers=None):
        return self.req(
            "PUT",
            f"inferences/{job_id}/start",
            headers=headers,
        )

    def get_training_job(self, job_id: str, headers=None):
        return self.req(
            "GET",
            f"trainings/{job_id}",
            headers=headers,
        )

    def get_inference_job(self, job_id: str, headers=None):
        return self.req(
            "GET",
            f"inferences/{job_id}",
            headers=headers
        )

    def list_datasets(self, headers=None, params=None):
        return self.req(
            "GET",
            "datasets",
            headers=headers,
            params=params
        )

    def get_dataset(self, name: str, headers=None):
        return self.req(
            "GET",
            f"datasets/{name}",
            headers=headers
        )

    def create_dataset(self, headers=None, data=None):
        return self.req(
            "POST",
            "datasets",
            headers=headers,
            data=data
        )

    def update_dataset(self, dataset_id: str, headers=None, data=None):
        return self.req(
            "PUT",
            f"datasets/{dataset_id}",
            headers=headers,
            data=data
        )

    def create_model(self, headers=None, data=None):
        return self.req(
            "POST",
            "models",
            headers=headers,
            data=data
        )

    def update_model(self, model_id: str, headers=None, data=None):
        return self.req(
            "PUT",
            f"models/{model_id}",
            headers=headers,
            data=data
        )

    def list_models(self, headers=None, params=None):
        return self.req(
            "GET",
            "models",
            headers=headers,
            params=params
        )

    def start_training_job(self, training_id: str, headers=None, data=None):
        return self.req(
            "PUT",
            f"trainings/{training_id}",
            headers=headers,
            data=data
        )

    def create_training_job(self, headers=None, data=None):
        return self.req(
            "POST",
            "trainings",
            headers=headers,
            data=data
        )

    def list_trainings(self, headers=None, params=None):
        return self.req(
            "GET",
            "trainings",
            headers=headers,
            params=params
        )

    def list_inferences(self, headers=None, params=None):
        return self.req(
            "GET",
            "inferences",
            headers=headers,
            params=params
        )
