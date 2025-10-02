from my_func import my_handler, LambdaAPIGWResponse
import json
import pytest
from datetime import datetime


@pytest.fixture(scope="session")
def dummy_http():
    return {
        "method": "POST",
        "path": "",
        "protocol": "",
        "sourceIp": "127.0.0.1",
        "userAgent": "",
    }


@pytest.fixture(scope="session")
def dummy_context(dummy_http):
    return {
        "accountId": "",
        "apiId": "",
        "domainName": "",
        "domainPrefix": "",
        "requestId": "",
        "routeKey": "",
        "stage": "",
        "time": "",
        "timeEpoch": datetime.now(),
        "http": dummy_http,
    }


@pytest.fixture(scope="session")
def dummy_event_frame(dummy_context):
    return {
        "version": "",
        "routeKey": "",
        "rawPath": "",
        "rawQueryString": "",
        "headers": {},
        "requestContext": dummy_context,
    }


@pytest.fixture(scope="session")
def valid_body():
    return json.dumps({"username": "bob", "email": "bob@localhost.com"})


@pytest.fixture(
    scope="session",
    params=[1, False],
    ids=[
        "invalid type (int)",
        "invalid type (bool)",
    ],
)
def invalid_body(request):
    return request.param


@pytest.fixture(scope="session")
def valid_event(dummy_event_frame, valid_body):
    return dummy_event_frame | {"body": valid_body}


@pytest.fixture(scope="session")
def invalid_event(dummy_event_frame, invalid_body):
    return dummy_event_frame | {"body": invalid_body}


def test_ok(valid_event):
    assert my_handler(
        event=valid_event,
        context="",  # type: ignore
    ) == LambdaAPIGWResponse(
        cookies=[],
        headers={"Content-Type": "application/json"},
        body=json.dumps({"message": "OK"}),
        isBase64Encoded=False,
        statusCode=200,
    )


def test_ng(invalid_event):
    assert my_handler(
        event=invalid_event,
        context="",  # type: ignore
    ) == LambdaAPIGWResponse(
        cookies=[],
        headers={"Content-Type": "application/json"},
        body=json.dumps({"error": "Bad Request"}),
        isBase64Encoded=False,
        statusCode=400,
    )
