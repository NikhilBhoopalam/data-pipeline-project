"""
Smoke-test: ensure lambda_handler returns 200 on an empty S3 event.
Run `pytest -q`.
"""
from lambda_function.lambda_function import lambda_handler


def test_lambda_basic():
    event = {"Records": []}
    assert lambda_handler(event, None)["statusCode"] == 200
