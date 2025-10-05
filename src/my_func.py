from boto3 import client
from botocore.config import Config
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayV2Envelope
from pydantic import ValidationError, BaseModel, ConfigDict, EmailStr
from typing import TypedDict, Literal
import json
from functools import partial
from os import environ
from time import time


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

# TODO: Config 設定
config = Config(
    # Dynamo DB にデフォルトのタイムアウト値 (60 秒) は過剰なので明示的に設定する
    connect_timeout=1,
    read_timeout=1,
    retries={
        "mode": "standard",
        "max_attempts": 2,
    },
)
db_client = client("dynamodb")


def add_user(username: str, email: EmailStr):
    print("Register user")
    tablename = environ["TABLENAME"]
    db_client.put_item(
        TableName=tablename,
        Item={
            "username": {"S": username},
            "email": {"S": email},
            # dynamodb では日時型の値は扱えないため、epoch 秒で保持する
            "accepted": {"N": f"{time()}"},
            # TODO: 特典の DL URL
        },
    )
    print("User registered")


def my_handler(event: dict, context: LambdaContext) -> LambdaAPIGWResponse:
    try:
        user_info = parse(event=event, model=UserInfo, envelope=ApiGatewayV2Envelope)
    except ValidationError as e:
        print(e.json())
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Bad Request"}), statusCode=400
        )

    print(user_info)

    try:
        add_user(username=user_info.username, email=user_info.email)
    except Exception as e:
        print(f"failed to register user: {e}")
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Internal Server Error"}), statusCode=400
        )

    return DEFAULT_RESUPONSE(
        statusCode=200,
        body=json.dumps({"message": "OK", "user_info": user_info.model_dump()}),
    )
