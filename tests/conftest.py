"""conftest.py"""

import os
from json import loads


# from moto import (
#     mock_dynamodb2,
#     mock_cognitoidp,
#     mock_lambda,
#     mock_iam,
# )
from pytest import fixture

basename = os.path.basename(__file__)
dirname = os.path.dirname(__file__)

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1))  # Minimal display to enable event posting
    yield
    pygame.quit()


class ContextMock(object):
    def __init__(self, environment="test"):
        self.invoked_function_arn = f"arn:{environment}"
        self.function_name = "function_name"
        self.function_version = "function_version"
        self.invoked_function_arn = "invoked_function_arn"
        self.memory_limit_in_mb = "memory_limit_in_mb"
        self.aws_request_id = "aws_request_id"
        self.log_group_name = "log_group_name"
        self.log_stream_name = "log_stream_name"
        self.millis = 0

    def get_remaining_time_in_millis(self):
        return self.millis

    def __setattr__(self, attr, value):
        super().__setattr__(attr, value)


@fixture(scope="module")
def mock_context(environment="test"):
    """

    Args:
        environment:

    Returns:

    """
    context = ContextMock(environment=environment)

    yield context


@fixture(scope="module")
def aws_credentials():
    """Mocked credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@fixture(scope="function")
def player0() -> dict:
    """Example for $default websocket request"""
    return loads(open(f"{dirname}/fixtures/player0.json").read())


@fixture(scope="function")
def player1() -> dict:
    """Example for $default websocket request"""
    return loads(open(f"{dirname}/fixtures/player1.json").read())


@fixture(scope="function")
def match_json() -> dict:
    """Example for $default websocket request"""
    return loads(open(f"{dirname}/fixtures/match.json").read())


# @fixture(scope="module")
# def iam_client(aws_credentials):
#     """Cognito IDP mock client"""
#     with mock_iam():
#         yield boto3.client("iam", region_name="us-east-1")
#
#
# @fixture(scope="module")
# def lambda_execution_role(iam_client):
#     iam_role_response = iam_client.create_role(
#         RoleName=os.getenv("LAMBDA_EXECUTION_ROLE_NAME"),
#         AssumeRolePolicyDocument=dumps(
#             {
#                 "Version": "2012-10-17",
#                 "Statement": [
#                     {
#                         "Effect": "Allow",
#                         "Principal": {
#                             "Service": "lambda.amazonaws.com"
#                         },
#                         "Action": "sts:AssumeRole"
#                     }
#                 ]
#             }
#         ),
#     )
#     return iam_role_response
#
#
# @fixture(scope="module")
# def lambda_client(aws_credentials):
#     """Cognito IDP mock client"""
#     with mock_lambda():
#         yield boto3.client("lambda", region_name="us-east-1")
#
#
# @fixture(scope="module")
# def cognito_idp(aws_credentials):
#     """Cognito IDP mock client"""
#     with mock_cognitoidp():
#         yield boto3.client("cognito-idp", region_name="us-east-1")
#
#
# @fixture(scope="module")
# def user_pool(cognito_idp):
#     """Cognito IDP mock client"""
#     user_pool = cognito_idp.create_user_pool(
#         PoolName=os.getenv("USER_POOL_NAME"),
#     )
#     os.environ["USER_POOL_ID"] = user_pool["UserPool"]["Id"]
#     yield user_pool
#
#
# @fixture(scope="module")
# def ddb_resource(aws_credentials):
#     """DynamoDB mock client"""
#     with mock_dynamodb2():
#         yield boto3.resource("dynamodb")
#
#
# @fixture(scope="module")
# def ddb_table(ddb_resource, connection, match, player0, player1):
#     """
#     data_table
#         Sets up the mock DynamoDB tables and documents.
#     Returns:
#
#     """
#     table_name = os.environ["TABLE_NAME"]
#     ddb_table = ddb_resource.create_table(
#         AttributeDefinitions=[
#             {"AttributeName": "id", "AttributeType": "S"},
#         ],
#         TableName=table_name,
#         KeySchema=[
#             {"AttributeName": "id", "KeyType": "HASH"},
#         ]
#     )
#     ddb_table.put_item(Item=connection)
#     ddb_table.put_item(Item=match)
#     ddb_table.put_item(Item=player0)
#     ddb_table.put_item(Item=player1)
#     return ddb_table
#
#
# @fixture(scope="module")
# def connection():
#     return loads(
#         open(f"{dirname}/tests/fixtures/connection.json").read()
#     )
#
# @fixture(scope="module")
# def match():
#     return loads(
#         open(f"{dirname}/tests/fixtures/match.json").read()
#     )
#
#
# @fixture(scope="module")
# def mock_api_gateway_managment_api():
#     api_gateway_managment_api = botocore.session.get_session().create_client('apigatewaymanagementapi')
#     with Stubber(api_gateway_managment_api) as stubber:
#         stubber.add_response('post_to_connection', {})
#         yield stubber
#
#
# @fixture(scope="module")
# def event_api_gateway_request_default() -> dict:
#     """Example for $default websocket request"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/websocket.default.json").read()
#     )
#
#
# @fixture(scope="module")
# def event_api_gateway_request_ping() -> dict:
#     """Example for $default websocket request"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/websocket.ping.json").read()
#     )
#
#
# @fixture(scope="module")
# def event_api_gateway_request_message() -> dict:
#     """Example for $default websocket request"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/websocket.message.json").read()
#     )
#
#
# @fixture(scope="module")
# def event_api_gateway_request_connect() -> dict:
#     """Example for $default websocket request"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/websocket.connect.json").read()
#     )
#
#
# @fixture(scope="module")
# def event_api_gateway_request_disconnect() -> dict:
#     """Example for $default websocket request"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/websocket.disconnect.json").read()
#     )
#
#
# @fixture(scope="module")
# def event_api_gateway_request_match() -> dict:
#     """Match request object"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/websocket.match.json").read()
#     )


# @fixture(scope="module")
# def match() -> dict:
#     """Match request object"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/match.json").read()
#     )
#
#
# @fixture(scope="module")
# def connection() -> dict:
#     """Match request object"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/connection.json").read()
#     )
#
#
# @fixture(scope="module")
# def event_api_gateway_request_match() -> dict:
#     """Match request object"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/websocket.match.json").read()
#     )
#
#
# @fixture(scope="module")
# def event_api_gateway_request_update() -> dict:
#     """Match request object"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/websocket.update.json").read()
#     )
#
#
# @fixture(scope="module")
# def admin_get_user_response() -> dict:
#     """Match request object"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/cognito.user_attributes.json").read()
#     )
#
#
# @fixture(scope="module")
# def custom_request_userpool_env() -> dict:
#     """Match request object"""
#     return loads(
#         open(f"{dirname}/tests/fixtures/custom.userpool_env.request.json").read()
#     )
