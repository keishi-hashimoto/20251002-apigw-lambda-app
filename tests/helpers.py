from mypy_boto3_dynamodb.type_defs import AttributeValueTypeDef


def get_value_from_attribute_type_def(val: AttributeValueTypeDef):
    _type = list(val.keys())[0]
    # AttributeValueTypeDef の実体は TypedDict なので特定のキーしか許容しないが、_type 変数に代入した時点で str と推論される
    value = val[_type]  # type: ignore
    if _type == "N":
        return float(value)
    else:
        return value
