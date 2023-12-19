import json
import logging
from decimal import Decimal
from typing import Optional, Any

logger = logging.getLogger('response')
logger.setLevel(logging.INFO)


class HttpStatusCode:
    OK = 200
    NoContent: int = 204
    BadRequest = 400
    Forbidden = 403
    NotFound = 404
    InternalServerError = 500


# Mapping status codes to descriptions
http_status_descriptions = {
    HttpStatusCode.OK: "OK",
    HttpStatusCode.NoContent: "No Content",
    HttpStatusCode.BadRequest: "Bad Request",
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

    payload['headers'] = headers

    body = {
        'statusCode': status_code,
    }

    if data:
        body['data'] = data
    if message:
        body['message'] = message

    if decimal:
        payload['body'] = json.dumps(body, default=dumps_default)
    else:
        payload['body'] = json.dumps(body)

    logging.info(f"Response: {payload}")

    return payload


def ok(data=None,
       message: str = http_status_descriptions[HttpStatusCode.OK],
       headers: Optional[dict[str, Any]] = None,
       decimal=None
       ):
    return response(HttpStatusCode.OK, data, message, headers, decimal)


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
