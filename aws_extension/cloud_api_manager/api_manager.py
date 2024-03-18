import logging

import requests

import utils
from aws_extension.auth_service.simple_cloud_auth import cloud_auth_manager, Admin_Role
from aws_extension.cloud_api_manager.api import api
from utils import has_config

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)
string_separator = "___"
last_evaluated_key = {}

class CloudApiManager:

    def __init__(self):
        self.auth_manger = cloud_auth_manager

    def _get_headers_by_user(self, username):
        if not username:
            return {
                'x-api-key': self.auth_manger.api_key,
                'Content-Type': 'application/json',
            }

        return {
            'username': username,
            'x-api-key': self.auth_manger.api_key,
            'Content-Type': 'application/json',
        }

    def sagemaker_endpoint_delete(self, delete_endpoint_list, username=""):

        if not delete_endpoint_list:
            return "No endpoint to delete"

        logger.debug(f"start delete sagemaker endpoint delete function")
        logger.debug(f"delete endpoint list: {delete_endpoint_list}")

        delete_endpoint_list = [item.split('+')[0] for item in delete_endpoint_list]
        logger.debug(f"delete endpoint list: {delete_endpoint_list}")
        payload = {
            "endpoint_name_list": delete_endpoint_list,
        }

        deployment_url = f"{self.auth_manger.api_url}endpoints"

        try:
            resp = requests.delete(deployment_url, json=payload, headers=self._get_headers_by_user(username))
            if resp.status_code != 204:
                raise Exception(resp.json()['message'])
            return "Delete Endpoint Successfully"
        except Exception as e:
            logger.error(e)
            return f"Failed to delete sagemaker endpoint with exception: {e}"

    def trains_delete(self, list, username=""):
        if not list:
            return "No trains to delete"

        payload = {
            "training_id_list": list,
        }

        url = f"{self.auth_manger.api_url}trainings"

        try:
            resp = requests.delete(url, json=payload, headers=self._get_headers_by_user(username))
            if resp.status_code != 204:
                raise Exception(resp.json()['message'])
            return "Delete Trainings Successfully"
        except Exception as e:
            logger.error(e)
            return f"Failed to delete trainings with exception: {e}"


    def sagemaker_deploy(self, endpoint_name,
                         endpoint_type,
                         instance_type,
                         initial_instance_count=1,
                         custom_docker_image_uri="",
                         custom_extensions="",
                         autoscaling_enabled=True,
                         user_roles=None,
                         min_instance_number=1,
                         username=""):
        """ Create SageMaker endpoint for GPU inference.
        Args:
            instance_type (string): the ML compute instance type.
            initial_instance_count (integer): Number of instances to launch initially.
        Returns:
            (None)
        """
        # function code to call sagemaker deploy api
        logger.debug(
            f"start deploying instance type: {instance_type} with count {initial_instance_count} with autoscaling {autoscaling_enabled}............")

        payload = {
            "endpoint_name": endpoint_name,
            "endpoint_type": endpoint_type,
            "instance_type": instance_type,
            "initial_instance_count": initial_instance_count,
            'min_instance_number': min_instance_number,
            # use initial_instance_count for user experience
            'max_instance_number': initial_instance_count,
            "autoscaling_enabled": autoscaling_enabled,
            "custom_docker_image_uri": custom_docker_image_uri,
            "custom_extensions": custom_extensions,
            'assign_to_roles': user_roles,
            "creator": username,
        }

        deployment_url = f"{self.auth_manger.api_url}endpoints"

        try:
            response = requests.post(deployment_url, json=payload, headers=self._get_headers_by_user(username))
            r = response.json()
            logger.debug(f"response for rest api {r}")
            return r['message']
        except Exception as e:
            logger.error(e)
            return f"Failed to start endpoint deployment with exception: {e}"

    def ckpts_delete(self, ckpts, user_token=""):
        logger.debug(f"ckpts: {ckpts}")

        data = {
            "checkpoint_id_list": ckpts,
        }

        try:
            api.set_username(user_token)
            resp = api.delete_checkpoints(data=data)
            if resp.status_code != 204:
                raise Exception(resp.json()['message'])
            return "Delete Checkpoints Successfully"
        except Exception as e:
            logger.error(e)
            return f"Failed to delete checkpoint with exception: {e}"

    def ckpt_rename(self, ckpt_id, name, user_token=""):
        data = {
            "name": name,
        }

        try:
            api.set_username(user_token)
            resp = api.update_checkpoint(checkpoint_id=ckpt_id, data=data)
            return resp.json()['message']
        except Exception as e:
            logger.error(e)
            return f"Failed to rename checkpoint with exception: {e}"


    def list_all_train_jobs_raw(self, username=None):
        if self.auth_manger.enableAuth and not username:
            return []

        if not self.auth_manger.api_url:
            return []

        response = requests.get(f'{self.auth_manger.api_url}trainings',
                                params={
                                    'username': username,
                                },
                                headers=self._get_headers_by_user(username))
        response.raise_for_status()
        r = response.json()
        if not r or r['statusCode'] != 200:
            logger.info(f"The API response is empty for trainings().{r['message']}")
            return []

        return r['data']['trainings']

    def list_all_sagemaker_endpoints_raw(self, username=None, user_token=""):
        if self.auth_manger.enableAuth and not user_token:
            return []

        if not self.auth_manger.api_url:
            return []

        response = requests.get(f'{self.auth_manger.api_url}endpoints',
                                params={
                                    'username': username,
                                },
                                headers=self._get_headers_by_user(user_token))
        response.raise_for_status()
        r = response.json()
        if not r or r['statusCode'] != 200:
            logger.info(f"The API response is empty for update_sagemaker_endpoints().{r['message']}")
            return []

        return r['data']['endpoints']

    def list_all_sagemaker_endpoints(self, username=None, user_token=""):
        try:
            if self.auth_manger.enableAuth and not user_token:
                return []

            if not has_config():
                return []

            response = requests.get(f'{self.auth_manger.api_url}endpoints',
                                    params={
                                        'username': username,
                                    },
                                    headers=self._get_headers_by_user(user_token))
            response.raise_for_status()
            r = response.json()
            if not r:
                logger.info("The API response is empty for update_sagemaker_endpoints().")
                return []

            sagemaker_raw_endpoints = []
            for obj in r['data']['endpoints']:
                if "EndpointDeploymentJobId" in obj:
                    if "endpoint_name" in obj:
                        endpoint_name = obj["endpoint_name"]
                        endpoint_status = obj["endpoint_status"]
                    else:
                        endpoint_name = obj["EndpointDeploymentJobId"]
                        endpoint_status = obj["status"]

                    if "endTime" in obj:
                        endpoint_time = obj["endTime"]
                    else:
                        endpoint_time = "N/A"

                    endpoint_info = f"{endpoint_name}+{endpoint_status}+{endpoint_time}"
                    sagemaker_raw_endpoints.append(endpoint_info)

            # Sort the list based on completeTime in descending order
            return sorted(sagemaker_raw_endpoints, key=lambda x: x.split('+')[-1], reverse=True)

        except Exception as e:
            logger.error(f"An error occurred while updating SageMaker endpoints: {e}")
            return []

    def list_all_ckpts(self, username=None, user_token=""):
        try:
            if self.auth_manger.enableAuth and not user_token:
                return []

            if not has_config():
                return []

            params = {
                'username': username,
                'per_page': 200,
            }

            api.set_username(username)
            response = api.list_checkpoints(params=params)
            r = response.json()
            if not r:
                logger.info("The API response is empty for update_sagemaker_endpoints().")
                return []

            ckpts_list = []
            for ckpt in r['data']['checkpoints']:
                if 'name' in ckpt and ckpt['name']:
                    ckpt_name = ckpt['name'][0]
                else:
                    ckpt_name = 'None'
                option_value = f"{ckpt_name}{string_separator}{ckpt['status']}{string_separator}{ckpt['id']}"
                ckpts_list.append(option_value)

            return sorted(ckpts_list, key=lambda x: x.split('+')[-1], reverse=True)

        except Exception as e:
            logger.error(f"list_all_ckpts: {e}")
            return []

    def get_user_by_username(self, username='', h_username='', show_password=False):
        if not self.auth_manger.enableAuth:
            return {
                'users': []
            }

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}users',
                                params={
                                    'username': username,
                                    'show_password': show_password
                                },
                                headers=self._get_headers_by_user(h_username))
        raw_resp.raise_for_status()
        logger.debug(raw_resp.json())
        resp = raw_resp.json()['data']
        return resp['users'][0]

    def list_users(self, username=""):
        if not self.auth_manger.enableAuth:
            return {
                'users': []
            }

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}users',
                                params={},
                                headers=self._get_headers_by_user(username))
        raw_resp.raise_for_status()
        return raw_resp.json()['data']

    def list_roles(self, username=""):
        if not self.auth_manger.enableAuth or not has_config():
            return {
                'roles': []
            }

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}roles', headers=self._get_headers_by_user(username))
        raw_resp.raise_for_status()
        return raw_resp.json()['data']

    def upsert_role(self, role_name, permissions, creator):
        if not self.auth_manger.enableAuth:
            return {}

        payload = {
            "role_name": role_name,
            "permissions": permissions,
            "creator": creator
        }

        raw_resp = requests.post(f'{cloud_auth_manager.api_url}roles', json=payload,
                                 headers=self._get_headers_by_user(creator))
        resp = raw_resp.json()
        if raw_resp.status_code != 200 and raw_resp.status_code != 201:
            raise Exception(resp['message'])

        return True

    def upsert_user(self, username, password, roles, creator, initial=False):
        if not self.auth_manger.enableAuth and not initial:
            return {}
        if not password or len(password) < 1:
            raise Exception('password should not be none')

        if initial:
            roles = [Admin_Role]
            cloud_auth_manager.refresh()

        payload = {
            "initial": initial,
            "username": username,
            "password": password,
            "roles": roles,
            "creator": creator,
        }

        raw_resp = requests.post(f'{cloud_auth_manager.api_url}users',
                                 json=payload,
                                 headers=self._get_headers_by_user(creator)
                                 )
        resp = raw_resp.json()
        if raw_resp.status_code != 201:
            raise Exception(resp['message'])

        cloud_auth_manager.update_gradio_auth()
        return True

    def delete_user(self, username, user_token=""):
        if not self.auth_manger.enableAuth:
            return {}

        if username == cloud_auth_manager.username:
            raise Exception('Cannot delete current user')

        payload = {
            "user_name_list": [username]
        }

        raw_resp = requests.delete(f'{cloud_auth_manager.api_url}users',
                                   json=payload,
                                   headers=self._get_headers_by_user(user_token))
        if raw_resp.status_code != 204:
            raise Exception(raw_resp.json()['message'])
        return True

    def list_models_on_cloud(self, username, types='Stable-diffusion', status='Active'):
        if not self.auth_manger.enableAuth:
            return []

        params = {
            'username': username,
            'types': types,
            'status': status
        }
        headers = self._get_headers_by_user(username)
        raw_resp = api.list_checkpoints(params=params, headers=headers)

        raw_resp.raise_for_status()
        checkpoints = []

        if 'data' not in raw_resp.json():
            return checkpoints

        resp = raw_resp.json()['data']
        for ckpt in resp['checkpoints']:
            if not ckpt or 'name' not in ckpt or not ckpt['name']:
                continue

            for name in ckpt['name']:
                if name not in checkpoints:
                    checkpoints.append({
                        'name': name,
                        'id': ckpt['id'],
                        's3Location': ckpt['s3Location'],
                        'type': ckpt['type'],
                        'status': ckpt['status'],
                        'created': float(ckpt['created']),
                        'allowed_roles_or_users': ckpt['allowed_roles_or_users'],
                    })

        return checkpoints

    def list_all_inference_jobs_on_cloud(self, target_task_type, username, first_load="first"):
        if not self.auth_manger.enableAuth:
            return []

        params = {
            'username': username,
            'type': target_task_type,
            'limit': 10,
        }

        global last_evaluated_key
        last_key_previous = f"{username}_{target_task_type}_previous"
        if last_key_previous not in last_evaluated_key:
            last_evaluated_key[last_key_previous] = []

        last_key_cur = f"{username}_{target_task_type}_cur"
        if last_key_cur not in last_evaluated_key:
            last_evaluated_key[last_key_cur] = []

        last_key_cur_key = f"{username}_{target_task_type}_cur_key"
        if last_key_cur_key not in last_evaluated_key:
            last_evaluated_key[last_key_cur_key] = None

        last_key_next = f"{username}_{target_task_type}_next"
        if last_key_next not in last_evaluated_key:
            last_evaluated_key[last_key_next] = None

        if first_load == "next":
            if last_evaluated_key[last_key_next]:
                last_evaluated_key[last_key_previous].append(last_evaluated_key[last_key_next])
                params['exclusive_start_key'] = last_evaluated_key[last_key_next]
            else:
                return last_evaluated_key[last_key_cur]
        elif first_load == "previous":
            if len(last_evaluated_key[last_key_previous]) > 0:
                pre_key = last_evaluated_key[last_key_previous].pop()
                if pre_key != last_evaluated_key[last_key_cur_key]:
                    params['exclusive_start_key'] = pre_key
                elif len(last_evaluated_key[last_key_previous]) > 0:
                    params['exclusive_start_key'] = last_evaluated_key[last_key_previous].pop()
        else:
            last_evaluated_key[last_key_next] = None
            last_evaluated_key[last_key_previous] = []

        if 'exclusive_start_key' in params:
            last_evaluated_key[last_key_cur_key] = params['exclusive_start_key']

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}inferences', params=params,
                                headers=self._get_headers_by_user(username))
        raw_resp.raise_for_status()
        resp = raw_resp.json()

        if 'last_evaluated_key' in resp['data']:
            last_evaluated_key[last_key_next] = resp['data']['last_evaluated_key']
        else:
            last_evaluated_key[last_key_next] = None

        last_evaluated_key[last_key_cur] = resp['data']['inferences']

        return resp['data']['inferences']

    def get_dataset_items_from_dataset(self, dataset_name, user_token=""):
        if not self.auth_manger.enableAuth:
            return []

        raw_response = requests.get(url=f'{self.auth_manger.api_url}datasets/{dataset_name}',
                                    headers=self._get_headers_by_user(user_token))
        raw_response.raise_for_status()

        return raw_response.json()['data']


api_manager = CloudApiManager()
