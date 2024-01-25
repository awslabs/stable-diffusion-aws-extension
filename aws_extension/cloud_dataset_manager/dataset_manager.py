import base64
import logging
import sys

import requests

from utils import get_variable_from_json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_sorted_cloud_dataset(username):
    url = get_variable_from_json("api_gateway_url") + "datasets?dataset_status=Enabled"
    api_key = get_variable_from_json("api_token")
    if not url or not api_key:
        logger.debug("Url or API-Key is not setting.")
        return []

    try:
        encode_type = "utf-8"
        raw_response = requests.get(
            url=url,
            headers={
                "x-api-key": api_key,
                "Authorization": f"Bearer {base64.b16encode(username.encode(encode_type)).decode(encode_type)}",
            },
        )
        raw_response.raise_for_status()
        response = raw_response.json()
        logger.info(f"datasets response: {response}")
        datasets = response["data"]["datasets"]
        datasets.sort(
            key=lambda t: t["timestamp"] if "timestamp" in t else sys.float_info.max,
            reverse=True,
        )
        return datasets
    except Exception as e:
        logger.error(f"exception {e}")
        return []
