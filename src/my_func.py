from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayV2Envelope
from pydantic import ValidationError, BaseModel, ConfigDict, EmailStr
from typing import TypedDict, Literal
import json
from functools import partial


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


def my_handler(event: dict, context: LambdaContext) -> LambdaAPIGWResponse:
    try:
        user_info = parse(event=event, model=UserInfo, envelope=ApiGatewayV2Envelope)
    except ValidationError as e:
        print(e.json())
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Bad Request"}), statusCode=400
        )

    print(user_info)

    return DEFAULT_RESUPONSE(
        statusCode=200,
        body=json.dumps({"message": "OK", "user_info": user_info.model_dump()}),
    )
