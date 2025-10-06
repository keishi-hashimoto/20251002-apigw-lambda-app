from my_func import add_user, db_client
from moto.core.models import patch_client

from helpers import assert_dynamodb_record


def test_ok(dummy_table, presigned_url):
    patch_client(db_client)
    username = "testuser"
    email = "testmail@localhost.com"

    with assert_dynamodb_record(
        username=username,
        email=email,
        presigned_url=presigned_url,
        tablename=dummy_table,
    ):
        add_user(username, email, presigned_url)
