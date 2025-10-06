from boto3 import client
from os import environ
from tracer import tracer
from aws_lambda_powertools import Logger
from pydantic import EmailStr
from textwrap import dedent

UTF_8 = "UTF-8"
ses_client = client("ses")
logger = Logger()

SUBJECT = "会員特典のご案内"
BODY_TEMPLATE = dedent("""
    {username} 様。
    この度は会員登録ありがとうございます。
    以下の URL から、会員特典をダウンロードください (有効期限は 10 分間となりますので、ご了承ください)。
    {presigned_url}        
""").strip()


@tracer.capture_method
def send_email(username: str, email: EmailStr, presigned_url: str):
    """Send presigned url by email to registered user.

    Arguments:
        username (str): name of the registered user.
        email (EmailStr): Email of the registered user.
        presigned_url (str): Presigned url to download present.

    Returns:
        SendEmailResponseTypeDef:
            Response of the ses_client.send_email.
            This is actually a dictionary with two fields, MessageId and ResponseMetadata.
            This return value is not used, but returned for tracer metadata.
    """
    logger.info("Send presigned url")
    from_email = environ["FROM_EMAIL"]
    result = ses_client.send_email(
        Source=from_email,
        Destination={"ToAddresses": [email]},
        Message={
            "Subject": {"Charset": UTF_8, "Data": SUBJECT},
            "Body": {
                "Text": {
                    "Charset": UTF_8,
                    "Data": BODY_TEMPLATE.format(
                        username=username, presigned_url=presigned_url
                    ),
                }
            },
        },
    )
    logger.info("Presigned url is sent")
    return result
