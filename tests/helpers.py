from mypy_boto3_dynamodb.type_defs import AttributeValueTypeDef
from moto.ses.models import SESBackend, Message
from send_email import SUBJECT, BODY_TEMPLATE
from contextlib import contextmanager
from time import time
from boto3 import client


def get_value_from_attribute_type_def(val: AttributeValueTypeDef):
    _type = list(val.keys())[0]
    # AttributeValueTypeDef の実体は TypedDict なので特定のキーしか許容しないが、_type 変数に代入した時点で str と推論される
    value = val[_type]  # type: ignore
    if _type == "N":
        return float(value)
    else:
        return value


def assert_sent_message(
    message: Message, from_email: str, to_email: str, username: str, presigned_url: str
):
    # message の型定義は以下
    # https://github.com/getmoto/moto/blob/f4db5af875245e0aff0a3166bdf267d6609fe08c/moto/ses/models.py#L82
    assert message.source == from_email
    assert message.destinations == {"ToAddresses": [to_email]}
    assert message.subject == SUBJECT
    assert message.body == BODY_TEMPLATE.format(
        username=username, presigned_url=presigned_url
    )


@contextmanager
def assert_ses_backend(
    ses_backend: SESBackend,
    from_email: str,
    to_email: str,
    username: str,
    presigned_url: str,
):
    assert ses_backend.sent_message_count == 0
    try:
        yield
    finally:
        assert ses_backend.sent_message_count == 1
        assert_sent_message(
            message=ses_backend.sent_messages[0],
            from_email=from_email,
            to_email=to_email,
            username=username,
            presigned_url=presigned_url,
        )


@contextmanager
def assert_no_mail_is_send(backend: SESBackend):
    assert backend.sent_message_count == 0
    try:
        yield
    finally:
        assert backend.sent_message_count == 0


@contextmanager
def assert_dynamodb_record(
    username: str,
    email: str,
    presigned_url: str,
    tablename: str,
):
    started = time()
    db_client = client("dynamodb")
    assert db_client.scan(TableName=tablename)["Count"] == 0
    yield
    ended = time()
    users = db_client.scan(TableName=tablename)["Items"]

    assert len(users) == 1
    user = users[0]
    assert get_value_from_attribute_type_def(user["username"]) == username
    assert get_value_from_attribute_type_def(user["email"]) == email
    assert started < get_value_from_attribute_type_def(user["accepted"]) < ended  # type: ignore
    assert get_value_from_attribute_type_def(user["presigned_url"]) == presigned_url
