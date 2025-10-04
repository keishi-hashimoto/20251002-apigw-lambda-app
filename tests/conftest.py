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
