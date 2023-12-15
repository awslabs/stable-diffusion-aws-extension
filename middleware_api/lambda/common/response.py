class HttpStatusCode:
    OK = 200
    NoContent: int = 204
    BadRequest = 400
    NotFound = 404
    InternalServerError = 500


# Mapping status codes to descriptions
http_status_descriptions = {
    HttpStatusCode.OK: "OK",
    HttpStatusCode.NoContent: "No Content",
    HttpStatusCode.BadRequest: "Bad Request",
    HttpStatusCode.NotFound: "Not Found",
    HttpStatusCode.InternalServerError: "Internal Server Error"
}


class StatusCode:
    def __init__(self, code):
        self.code = code
        self.description = http_status_descriptions.get(code, "Unknown Status Code")

    def __str__(self):
        return f"Status Code: {self.code} - {self.description}"


def response(status_code: int, data=None, message: str = None):
    payload = {
        'statusCode': status_code,
    }

    if data:
        payload['body'] = data
    if message:
        payload['message'] = message

    return payload


def ok(data=None, message: str = http_status_descriptions[HttpStatusCode.OK]):
    return response(HttpStatusCode.OK, data, message)


def no_content(data=None, message: str = http_status_descriptions[HttpStatusCode.NoContent]):
    return response(HttpStatusCode.NoContent, data, message)


def bad_request(data=None, message: str = http_status_descriptions[HttpStatusCode.BadRequest]):
    return response(HttpStatusCode.BadRequest, data, message)


def not_found(data=None, message: str = http_status_descriptions[HttpStatusCode.NotFound]):
    return response(HttpStatusCode.NotFound, data, message)


def internal_server_error(data=None, message: str = http_status_descriptions[HttpStatusCode.InternalServerError]):
    return response(HttpStatusCode.NotFound, data, message)
