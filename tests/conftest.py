from moto import mock_aws
from pytest import fixture
from boto3 import client
from os import environ


@fixture
def mock_start():
    with mock_aws():
        yield


@fixture
def db_client(mock_start):
    return client("dynamodb")


@fixture(autouse=True)
def dummy_table(db_client):
    tablename = environ["TABLENAME"]
    db_client.create_table(
        TableName=tablename,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    return tablename


@fixture(scope="session")
def presigned_url():
    return "https://dummy-bucket.s3.amazonaws.com/dummy.html?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=dummy%2F20251006%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20251006T032350Z&X-Amz-Expires=600&X-Amz-SignedHeaders=host&X-Amz-Signature=*****************"
