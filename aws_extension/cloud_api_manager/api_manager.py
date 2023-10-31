import base64
import json
import logging

import requests

import utils
from aws_extension.auth_service.simple_cloud_auth import cloud_auth_manager

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)
encode_type = "utf-8"


class CloudApiManager:

    def __init__(self):
        self.auth_manger = cloud_auth_manager

    # todo: not sure how to get current login user's password from gradio
    # todo: use username only for authorize checking for now only, e.g. user_token = username
    def _get_headers_by_user(self, user_token):
        if not user_token:
            return {
                'x-api-key': self.auth_manger.api_key,
                'Content-Type': 'application/json',
            }
        _auth_token = f'Bearer {base64.b16encode(user_token.encode(encode_type)).decode(encode_type)}'
        return {
            'Authorization': _auth_token,
            'x-api-key': self.auth_manger.api_key,
            'Content-Type': 'application/json',
        }

    def sagemaker_deploy(self, endpoint_name, instance_type, initial_instance_count=1,
                         autoscaling_enabled=True, user_roles=None, user_token=""):
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
            "instance_type": instance_type,
            "initial_instance_count": initial_instance_count,
            "autoscaling_enabled": autoscaling_enabled,
            'assign_to_roles': user_roles
        }

        deployment_url = f"{self.auth_manger.api_url}inference/deploy-sagemaker-endpoint"

        try:
            response = requests.post(deployment_url, json=payload, headers=self._get_headers_by_user(user_token))
            r = response.json()
            logger.debug(f"response for rest api {r}")
            return "Endpoint deployment started"
        except Exception as e:
            logger.error(e)
            return f"Failed to start endpoint deployment with exception: {e}"

    def sagemaker_endpoint_delete(self, delete_endpoint_list, user_token=""):
        logger.debug(f"start delete sagemaker endpoint delete function")
        logger.debug(f"delete endpoint list: {delete_endpoint_list}")

        delete_endpoint_list = [item.split('+')[0] for item in delete_endpoint_list]
        logger.debug(f"delete endpoint list: {delete_endpoint_list}")
        payload = {
            "delete_endpoint_list": delete_endpoint_list,
        }

        deployment_url = f"{self.auth_manger.api_url}endpoints"

        try:
            response = requests.delete(deployment_url, json=payload, headers=self._get_headers_by_user(user_token))
            r = response.json()
            logger.debug(f"response for rest api {r}")
            return r
        except Exception as e:
            logger.error(e)
            return f"Failed to delete sagemaker endpoint with exception: {e}"

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
            logger.info(f"The API response is empty for update_sagemaker_endpoints().{r['errMsg']}")
            return []

        return r['endpoints']

    def list_all_sagemaker_endpoints(self, username=None, user_token=""):
        try:
            if self.auth_manger.enableAuth and not user_token:
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
            for obj in r['endpoints']:
                if "EndpointDeploymentJobId" in obj:
                    if "endpoint_name" in obj:
                        endpoint_name = obj["endpoint_name"]
                        endpoint_status = obj["endpoint_status"]
                    else:
                        endpoint_name = obj["EndpointDeploymentJobId"]
                        endpoint_status = obj["status"]

                    # Skip if status is 'Deleted'
                    if endpoint_status == 'Deleted':
                        continue

                    # Compatible with fields used in older versions
                    if obj["status"] == 'deleted':
                        continue

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

    def get_user_by_username(self, username='', user_token='', show_password=False):
        if not self.auth_manger.enableAuth:
            return {
                'users': []
            }

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}users',
                                params={
                                    'username': username,
                                    'show_password': show_password
                                },
                                headers=self._get_headers_by_user(user_token))
        raw_resp.raise_for_status()
        return raw_resp.json()['users'][0]

    def list_users(self, limit=10, last_evaluated_key="", user_token=""):
        if not self.auth_manger.enableAuth:
            return {
                'users': []
            }

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}users',
                                params={
                                    'limit': limit,
                                    'last_evaluated_key': json.dumps(last_evaluated_key)
                                },
                                headers=self._get_headers_by_user(user_token))
        raw_resp.raise_for_status()
        return raw_resp.json()

    def list_roles(self, user_token=""):
        if not self.auth_manger.enableAuth:
            return {
                'roles': []
            }

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}roles', headers=self._get_headers_by_user(user_token))
        raw_resp.raise_for_status()
        return raw_resp.json()

    def upsert_role(self, role_name, permissions, creator, user_token=""):
        if not self.auth_manger.enableAuth:
            return {}

        payload = {
            "role_name": role_name,
            "permissions": permissions,
            "creator": creator
        }

        raw_resp = requests.post(f'{cloud_auth_manager.api_url}role', json=payload, headers=self._get_headers_by_user(user_token))
        raw_resp.raise_for_status()
        resp = raw_resp.json()
        if resp['statusCode'] != 200:
            raise Exception(resp['errMsg'])

        return True

    def upsert_user(self, username, password, roles, creator, initial=False, user_token=""):
        if not self.auth_manger.enableAuth and not initial:
            return {}
        if not password.strip() or len(password.strip()) < 1:
            raise Exception('password should not be none')
        payload = {
            "initial": initial,
            "username": username,
            "password": password,
            "roles": roles,
            "creator": creator,
        }

        if initial:
            cloud_auth_manager.refresh()

        raw_resp = requests.post(f'{cloud_auth_manager.api_url}user',
                                 json=payload,
                                 headers=self._get_headers_by_user(user_token)
                                 )
        raw_resp.raise_for_status()
        resp = raw_resp.json()
        if resp['statusCode'] != 200:
            raise Exception(resp['errMsg'])

        cloud_auth_manager.update_gradio_auth()
        return True

    def delete_user(self, username, user_token=""):
        if not self.auth_manger.enableAuth:
            return {}

        raw_resp = requests.delete(f'{cloud_auth_manager.api_url}user/{username}',
                                   headers=self._get_headers_by_user(user_token))
        raw_resp.raise_for_status()
        resp = raw_resp.json()
        if resp['statusCode'] != 200:
            raise Exception(resp['errMsg'])
        return True

    def list_models_on_cloud(self, username, user_token="", types='Stable-diffusion', status='Active'):
        if not self.auth_manger.enableAuth:
            return []

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}checkpoints', params={
            'username': username,
            'types': types,
            'status': status
        }, headers=self._get_headers_by_user(user_token))

        raw_resp.raise_for_status()
        checkpoints = []
        resp = raw_resp.json()
        for ckpt in resp['checkpoints']:
            for name in ckpt['name']:
                if name not in checkpoints:
                    checkpoints.append({
                        'name': name,
                        'id': ckpt['id'],
                        's3Location': ckpt['s3Location'],
                        'type': ckpt['type'],
                        'status': ckpt['status'],
                        'created': ckpt['created'],
                        'allowed_roles_or_users': ckpt['allowed_roles_or_users'],
                    })

        return checkpoints

    def list_all_inference_jobs_on_cloud(self, username, user_token=""):
        if not self.auth_manger.enableAuth:
            return []

        raw_resp = requests.get(url=f'{self.auth_manger.api_url}inferences', params={
            'username': username,
        }, headers=self._get_headers_by_user(user_token))
        raw_resp.raise_for_status()
        resp = raw_resp.json()
        return resp['inferences']


api_manager = CloudApiManager()
