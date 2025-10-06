from boto3 import client
from botocore.config import Config
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayV2Envelope
from pydantic import ValidationError, BaseModel, ConfigDict, EmailStr
from typing import TypedDict, Literal
import json
from functools import partial
from os import environ
from time import time

from tracer import tracer
from send_email import send_email

logger = Logger()


class UserInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    email: EmailStr


class LambdaAPIGWResponse(TypedDict):
    cookies: list[str]
    headers: dict[str, str]
    statusCode: int
    body: str
    isBase64Encoded: Literal[False]


DEFAULT_RESUPONSE = partial(
    LambdaAPIGWResponse,
    cookies=[],
    headers={"Content-Type": "application/json"},
    isBase64Encoded=False,
)

config = Config(
    # Dynamo DB にデフォルトのタイムアウト値 (60 秒) は過剰なので明示的に設定する
    connect_timeout=1,
    read_timeout=1,
    retries={
        "mode": "standard",
        "max_attempts": 2,
    },
)
db_client = client("dynamodb", config=config)

# 署名付き URL の最新バージョンは v4 だが、boto3 のデフォルト値は v2 なので明示的な指定が必要
s3_client = client("s3", config=Config(signature_version="s3v4"))


@tracer.capture_method
def generate_presigned_url() -> str:
    bucket = environ["PRESENT_BUCKET"]
    key = environ["PRESENT_KEY"]

    logger.info("Start to generate presigned url")

    presigned_url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        HttpMethod="GET",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=10 * 60,  # デフォルトの 1 時間だと長すぎるので 10 分
    )
    logger.info("Finished to generate presigned url")
    return presigned_url


@tracer.capture_method
def add_user(username: str, email: EmailStr, presigned_url: str):
    logger.info("Register user")
    tablename = environ["TABLENAME"]
    db_client.put_item(
        TableName=tablename,
        Item={
            "username": {"S": username},
            "email": {"S": email},
            # dynamodb では日時型の値は扱えないため、epoch 秒で保持する
            "accepted": {"N": f"{time()}"},
            "presigned_url": {"S": presigned_url},
        },
    )
    logger.info("User registered")


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def my_handler(event: dict, context: LambdaContext) -> LambdaAPIGWResponse:
    try:
        user_info = parse(event=event, model=UserInfo, envelope=ApiGatewayV2Envelope)
    except ValidationError as e:
        logger.error(e.json())
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Bad Request"}), statusCode=400
        )

    logger.info(user_info)
    username = user_info.username
    email = user_info.email

    try:
        presigned_url = generate_presigned_url()
    except ClientError as e:
        logger.error(f"failed to generate presigned url: {e.response}")
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Internal Server Error"}),
            statusCode=e.response["ResponseMetadata"]["HTTPStatusCode"],  # type: ignore
        )
    except Exception as e:
        logger.error(f"failed to generate presigned url: {e}")
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Internal Server Error"}), statusCode=500
        )

    try:
        send_email(username, email, presigned_url)
    except ClientError as e:
        logger.error(f"failed to send email: {e.response}")
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Internal Server Error"}),
            statusCode=e.response["ResponseMetadata"]["HTTPStatusCode"],  # type: ignore
        )
    except Exception as e:
        logger.error(f"failed to send email: {e}")
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Internal Server Error"}), statusCode=500
        )

    try:
        add_user(
            username=user_info.username,
            email=user_info.email,
            presigned_url=presigned_url,
        )
    except ClientError as e:
        logger.error(f"failed to register user: {e.response}")
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Internal Server Error"}),
            statusCode=e.response["ResponseMetadata"]["HTTPStatusCode"],  # type: ignore
        )
    except Exception as e:
        logger.error(f"failed to register user: {e}")
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Internal Server Error"}), statusCode=500
        )

    return DEFAULT_RESUPONSE(
        statusCode=200,
        body=json.dumps({"message": "OK", "user_info": user_info.model_dump()}),
    )
