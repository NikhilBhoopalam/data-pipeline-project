"""
Smoke-test: ensure lambda_handler returns 200 on an empty S3 event.
Run `pytest -q`.
"""

from lambda_function.lambda_function import lambda_handler


def test_lambda_basic():
    event = {"Records": []}
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200


def test_lambda_no_records():
    event = {"Records": []}
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
