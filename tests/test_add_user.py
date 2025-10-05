from my_func import add_user, db_client
from moto.core.models import patch_client

from time import time
from helpers import get_value_from_attribute_type_def


def test_ok(dummy_table):
    patch_client(db_client)
    username = "testuser"
    email = "testmail@localhost.com"

    started = time()
    add_user(username, email)
    ended = time()

    users = db_client.scan(TableName=dummy_table)["Items"]

    assert len(users) == 1
    user = users[0]
    assert get_value_from_attribute_type_def(user["username"]) == username
    assert get_value_from_attribute_type_def(user["email"]) == email
    assert started < get_value_from_attribute_type_def(user["accepted"]) < ended  # type: ignore
