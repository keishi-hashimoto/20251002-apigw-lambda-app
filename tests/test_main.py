from my_func import my_handler, LambdaAPIGWResponse, db_client
from send_email import ses_client
import json
import pytest
from datetime import datetime
from moto.core.models import patch_client

from os import environ
from dataclasses import dataclass
from unittest.mock import patch

from helpers import assert_ses_backend, assert_no_mail_is_send, assert_dynamodb_record


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


@pytest.fixture(scope="session")
def lambda_context():
    # aws_powertools の LambdaContext はコンストラクタを持たないので、型定義は自作する必要がある
    @dataclass
    class LambdaContext:
        # ログ出力用のダミーのため、最低限必要なフィールドのみを定義する
        function_name: str
        invoked_function_arn: str
        memory_limit_in_mb: int
        aws_request_id: str

    return LambdaContext(
        function_name="my_func",
        invoked_function_arn="*****",
        memory_limit_in_mb=1,
        aws_request_id="++++",
    )


def test_ok(
    valid_event,
    dummy_table,
    lambda_context,
    presigned_url,
    ses_backend,
    from_email,
):
    patch_client(db_client)
    patch_client(ses_client)
    body = json.loads(valid_event["body"])
    username = body["username"]
    email = body["email"]

    with (
        patch("my_func.generate_presigned_url") as patched,
        assert_ses_backend(
            ses_backend=ses_backend,
            from_email=from_email,
            to_email=email,
            username=username,
            presigned_url=presigned_url,
        ),
        assert_dynamodb_record(
            username=username,
            email=email,
            presigned_url=presigned_url,
            tablename=dummy_table,
        ),
    ):
        patched.return_value = presigned_url

        assert my_handler(
            event=valid_event,
            context=lambda_context,
        ) == LambdaAPIGWResponse(
            cookies=[],
            headers={"Content-Type": "application/json"},
            body=json.dumps({"message": "OK"} | {"user_info": body}),
            isBase64Encoded=False,
            statusCode=200,
        )


def test_invalid_event(invalid_event, dummy_table, lambda_context, ses_backend):
    patch_client(db_client)
    patch_client(ses_client)

    with assert_no_mail_is_send(backend=ses_backend):
        assert my_handler(
            event=invalid_event,
            context=lambda_context,
        ) == LambdaAPIGWResponse(
            cookies=[],
            headers={"Content-Type": "application/json"},
            body=json.dumps({"error": "Bad Request"}),
            isBase64Encoded=False,
            statusCode=400,
        )

        users = db_client.scan(TableName=dummy_table)["Items"]

        assert len(users) == 0


def test_invalid_tablename(
    valid_event,
    dummy_table,
    lambda_context,
    from_email,
    presigned_url,
    ses_backend,
):
    environ["TABLENAME"] = f"{dummy_table}_dummy"
    patch_client(db_client)
    patch_client(ses_client)

    body = json.loads(valid_event["body"])
    username = body["username"]
    email = body["email"]

    # DB への登録はメール送信よりも後なので、メール送信自体は行われる
    with (
        patch("my_func.generate_presigned_url") as patched,
        assert_ses_backend(
            ses_backend=ses_backend,
            from_email=from_email,
            to_email=email,
            username=username,
            presigned_url=presigned_url,
        ),
    ):
        patched.return_value = presigned_url
        try:
            assert my_handler(
                event=valid_event,
                context=lambda_context,
            ) == LambdaAPIGWResponse(
                cookies=[],
                headers={"Content-Type": "application/json"},
                body=json.dumps({"error": "Internal Server Error"}),
                isBase64Encoded=False,
                statusCode=400,
            )
            users = db_client.scan(TableName=dummy_table)["Items"]

            assert len(users) == 0
        finally:
            environ["TABLENAME"] = dummy_table
