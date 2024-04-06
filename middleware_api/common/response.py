import json
import logging
import os
import urllib.parse
from decimal import Decimal
from typing import Optional, Any

from aws_lambda_powertools import Tracer

url_suffix = os.environ.get("URL_SUFFIX")

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
tracer = Tracer()
x_api_version = "1.5.0"


class HttpStatusCode:
    OK = 200
    Created = 201
    Accepted = 202
    NoContent: int = 204
    BadRequest = 400
    Unauthorized = 401
    Forbidden = 403
    NotFound = 404
    InternalServerError = 500


# Mapping status codes to descriptions
http_status_descriptions = {
    HttpStatusCode.OK: "OK",
    HttpStatusCode.Created: "Created",
    HttpStatusCode.Accepted: "Accepted",
    HttpStatusCode.NoContent: "No Content",
    HttpStatusCode.BadRequest: "Bad Request",
    HttpStatusCode.Unauthorized: "Unauthorized",
    HttpStatusCode.Forbidden: "Forbidden",
    HttpStatusCode.NotFound: "Not Found",
    HttpStatusCode.InternalServerError: "Internal Server Error"
}


class StatusCode:
    def __init__(self, code):
        self.code = code
        self.description = http_status_descriptions.get(code, "Unknown Status Code")

    def __str__(self):
        return f"Status Code: {self.code} - {self.description}"


def dumps_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError("Object of type 'Decimal' is not JSON serializable")


@tracer.capture_method
def response(status_code: int, data=None, message: str = None, headers: Optional[dict[str, Any]] = None, decimal=None):
    payload = {
        'isBase64Encoded': False,
        'statusCode': status_code,
    }

    if headers is None:
        headers = {
            'Content-Type': 'application/json',
        }
    else:
        headers['Content-Type'] = 'application/json'

    headers['x-api-version'] = x_api_version

    headers['Access-Control-Allow-Origin'] = '*'
    headers['Access-Control-Allow-Headers'] = '*'
    headers['Access-Control-Allow-Methods'] = '*'
    headers['Access-Control-Allow-Credentials'] = True

    payload['headers'] = headers

    body = {
        'statusCode': status_code,
        'debug': get_debug(),
    }

    if data:
        body['data'] = data
    if message:
        body['message'] = message

    if decimal:
        payload['body'] = json.dumps(body, default=dumps_default)
    else:
        payload['body'] = json.dumps(body)

    logger.info("Lambda Response Payload:")
    logger.info(payload['body'])

    return payload


def get_debug():
    aws_lambda_log_group_name = os.environ.get('AWS_LAMBDA_LOG_GROUP_NAME')
    aws_lambda_function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
    aws_lambda_log_stream_name = os.environ.get('AWS_LAMBDA_LOG_STREAM_NAME')
    _x_amzn_trace_id = os.environ.get('_X_AMZN_TRACE_ID')
    region = os.environ.get('AWS_DEFAULT_REGION')

    log_group_name = urllib.parse.quote(aws_lambda_log_group_name, safe='')
    log_stream_name = urllib.parse.quote(aws_lambda_log_stream_name, safe='')

    if url_suffix == "amazonaws.com.cn":
        region = "amazonaws.cn"

    log_url = (f"https://{region}.console.{url_suffix}/cloudwatch/home?region={region}"
               f"#logsV2:log-groups/log-group/{log_group_name}/log-events/{log_stream_name}")

    function_url = (f"https://{region}.console.{url_suffix}/lambda/home?region={region}"
                    f"#/functions/{aws_lambda_function_name}")

    trace_url = None
    if _x_amzn_trace_id:
        trace_id = _x_amzn_trace_id.split(';')[0].split('=')[1]
        trace_url = (f"https://{region}.console.{url_suffix}/cloudwatch/home?region={region}"
                     f"#xray:traces/{trace_id}")

    return {
        'function_url': function_url,
        'log_url': log_url,
        'trace_url': trace_url,
    }


def ok(data=None,
       message: str = http_status_descriptions[HttpStatusCode.OK],
       headers: Optional[dict[str, Any]] = None,
       decimal=None
       ):
    return response(HttpStatusCode.OK, data, message, headers, decimal)


def created(data=None,
            message: str = http_status_descriptions[HttpStatusCode.Created],
            headers: Optional[dict[str, Any]] = None,
            decimal=None
            ):
    return response(HttpStatusCode.Created, data, message, headers, decimal)


def accepted(data=None,
             message: str = http_status_descriptions[HttpStatusCode.Accepted],
             headers: Optional[dict[str, Any]] = None,
             decimal=None
             ):
    return response(HttpStatusCode.Accepted, data, message, headers, decimal)


def no_content(data=None,
               message: str = http_status_descriptions[HttpStatusCode.NoContent],
               headers: Optional[dict[str, Any]] = None,
               decimal=None
               ):
    return response(HttpStatusCode.NoContent, data, message, headers, decimal)


def bad_request(data=None,
                message: str = http_status_descriptions[HttpStatusCode.BadRequest],
                headers: Optional[dict[str, Any]] = None,
                decimal=None
                ):
    return response(HttpStatusCode.BadRequest, data, message, headers, decimal)


def unauthorized(data=None,
                 message: str = http_status_descriptions[HttpStatusCode.Unauthorized],
                 headers: Optional[dict[str, Any]] = None,
                 decimal=None
                 ):
    return response(HttpStatusCode.Unauthorized, data, message, headers, decimal)


def forbidden(data=None,
              message: str = http_status_descriptions[HttpStatusCode.Forbidden],
              headers: Optional[dict[str, Any]] = None,
              decimal=None
              ):
    return response(HttpStatusCode.Forbidden, data, message, headers, decimal)


def not_found(data=None,
              message: str = http_status_descriptions[HttpStatusCode.NotFound],
              headers: Optional[dict[str, Any]] = None,
              decimal=None
              ):
    return response(HttpStatusCode.NotFound, data, message, headers, decimal)


def internal_server_error(data=None,
                          message: str = http_status_descriptions[HttpStatusCode.InternalServerError],
                          headers: Optional[dict[str, Any]] = None,
                          decimal=None):
    return response(HttpStatusCode.InternalServerError, data, message, headers, decimal)
