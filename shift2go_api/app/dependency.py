from starlette.datastructures import State
from starlette.requests import Request


def get_state(request: Request) -> State:
    return request.app.state