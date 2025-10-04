from my_func import my_handler, LambdaAPIGWResponse, db_client
import json
import pytest
from datetime import datetime
from moto.core.models import patch_client

from time import time
from helpers import get_value_from_attribute_type_def
from os import environ


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
    params=[
        1,
        False,
        json.dumps({"email": "bob@localhost.com"}),
        json.dumps({"username": "bob"}),
        json.dumps(
            {"username": "bob", "email": "bob@localhost.com", "password": "..."}
        ),
        json.dumps({"username": 1, "email": "bob@localhost.com"}),
        json.dumps({"username": "bob", "email": "boblocalhost.com"}),
    ],
    ids=[
        "invalid type (int)",
        "invalid type (bool)",
        "username is missing",
        "email is missing",
        "additional field (password)",
        "field type is invald",
        "email format is invalid",
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


def test_ok(valid_event, dummy_table):
    patch_client(db_client)
    body = json.loads(valid_event["body"])
    username = body["username"]
    email = body["email"]
    started = time()

    assert my_handler(
        event=valid_event,
        context="",  # type: ignore
    ) == LambdaAPIGWResponse(
        cookies=[],
        headers={"Content-Type": "application/json"},
        body=json.dumps({"message": "OK"} | {"user_info": body}),
        isBase64Encoded=False,
        statusCode=200,
    )
    ended = time()

    users = db_client.scan(TableName=dummy_table)["Items"]

    assert len(users) == 1
    user = users[0]
    print(user["accepted"])
    assert get_value_from_attribute_type_def(user["username"]) == username
    assert get_value_from_attribute_type_def(user["email"]) == email
    assert started < get_value_from_attribute_type_def(user["accepted"]) < ended  # type: ignore


def test_invalid_event(invalid_event, dummy_table):
    patch_client(db_client)
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

    users = db_client.scan(TableName=dummy_table)["Items"]

    assert len(users) == 0


def test_valid_tablename(valid_event, dummy_table):
    environ["TABLENAME"] = f"{dummy_table}_dummy"
    patch_client(db_client)

    try:
        assert my_handler(
            event=valid_event,
            context="",  # type: ignore
        ) == LambdaAPIGWResponse(
            cookies=[],
            headers={"Content-Type": "application/json"},
            body=json.dumps({"error": "Internal Server Error"}),
            isBase64Encoded=False,
            statusCode=400,
        )
    finally:
        environ["TABLENAME"] = dummy_table
