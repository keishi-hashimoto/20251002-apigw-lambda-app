from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.models import APIGatewayProxyEventV2Model
from pydantic import ValidationError
from typing import TypedDict, Literal
import json
from functools import partial


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
        parsed_event = parse(event=event, model=APIGatewayProxyEventV2Model)
    except ValidationError as e:
        print(e.json())
        return DEFAULT_RESUPONSE(
            body=json.dumps({"error": "Bad Request"}), statusCode=400
        )

    body = parsed_event.body
    print(body)

    return DEFAULT_RESUPONSE(statusCode=200, body=json.dumps({"message": "OK"}))
