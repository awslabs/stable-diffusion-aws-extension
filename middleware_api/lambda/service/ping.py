import logging

from common.response import ok, bad_request


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, ctx):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {ctx}')

    return ok(message='pong')
