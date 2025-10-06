from moto.core.models import patch_client
from send_email import send_email, ses_client
from helpers import assert_ses_backend


def test_ok(presigned_url, ses_backend, from_email):
    patch_client(ses_client)
    username = "dummyuser"
    email = "dummy@localhost.com"

    # メール送信前後の SES Backend の状態確認は、このコンテキストマネージャで行う
    with assert_ses_backend(
        ses_backend=ses_backend,
        from_email=from_email,
        username=username,
        to_email=email,
        presigned_url=presigned_url,
    ):
        send_email(username, email, presigned_url)
