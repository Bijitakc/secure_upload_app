from functools import wraps
from flask import request, abort
from core.utils import token_decode


def login_required(func):
    """
    Decorator to check the validity of the Auth0 JWT
    """
    @wraps(func)
    def wrap(*args, **kwargs):
        authorization = request.headers.get("authorization", None)
        if not authorization:
            abort(401)
        token = authorization.split(' ')[1]
        token_decode_resp = token_decode(token)
        if token_decode_resp['error'] is True:
            return ({
                "error": token_decode_resp['error_message']
            }), 401
        return func(*args, **kwargs)

    return wrap
