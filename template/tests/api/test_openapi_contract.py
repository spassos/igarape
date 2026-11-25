"""Contract tests generated from the OpenAPI schema (Schemathesis).

Test level: API contract / fuzzing, in-process. Runs in `make test-unit` and `make check`
without Docker. Schemathesis loads `/openapi.json` from the same in-memory app the `client`
fixture builds and generates valid and invalid requests for every operation:
- with a valid token (`make_auth_headers`), every response must not be a server error and must
  match the documented status codes, content types and schemas;
- without credentials, no `/v1` operation may succeed, valid requests get `401`, and the
  problem+json responses (with `WWW-Authenticate`) must match what OpenAPI declares.

Flakiness control: Hypothesis is derandomized (the same examples on every run), bounded in
examples, has no deadline and keeps no example database, so a failure reproduces anywhere.
"""

from collections.abc import Mapping
from typing import Any

import pytest
import schemathesis
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, settings
from schemathesis import BaseSchema, Case, GenerationMode, Response
from schemathesis.checks import (
    content_type_conformance,
    not_a_server_error,
    response_headers_conformance,
    response_schema_conformance,
    status_code_conformance,
)

from tests.conftest import MakeAuthHeaders

CHECKS = [
    not_a_server_error,
    status_code_conformance,
    content_type_conformance,
    response_schema_conformance,
    response_headers_conformance,
]
# Responses the app really returns but OpenAPI does not declare yet, by operation. Remove an entry
# once the route declares it; `test_known_gaps_are_still_undocumented` enforces that.
# POST /v1/items: a body that is not decodable JSON is rejected with 400 before validation.
# Status codes an operation may return but does not document yet. Keep it empty: a test fails
# as soon as a listed gap gets documented, so the list cannot go stale.
UNDOCUMENTED_STATUS_CODES: Mapping[str, frozenset[int]] = {}
CONTRACT = settings(
    max_examples=30,
    derandomize=True,
    deadline=None,
    database=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)


@pytest.fixture
def contract_headers(make_auth_headers: MakeAuthHeaders) -> dict[str, str]:
    """A valid bearer token with every scope, so generated requests reach the route logic."""
    return make_auth_headers()


@pytest.fixture
def api_schema(client: TestClient) -> BaseSchema:
    return schemathesis.openapi.from_asgi("/openapi.json", client.app)


schema = schemathesis.pytest.from_fixture("api_schema")


@schema.parametrize()
@CONTRACT
def test_api_honors_its_openapi_contract(case: Case[Any], contract_headers: dict[str, str]) -> None:
    response = case.call(headers=contract_headers)

    validate(case, response, headers=contract_headers)


@schema.include(path_regex="^/v1/").parametrize()
@settings(CONTRACT, max_examples=10)
def test_business_routes_reject_anonymous_callers(case: Case[Any]) -> None:
    response = case.call()

    validate(case, response)
    assert not 200 <= response.status_code < 300
    if case.meta is not None and case.meta.generation.mode is GenerationMode.POSITIVE:
        assert response.status_code == 401


def test_known_gaps_are_still_undocumented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for label, codes in UNDOCUMENTED_STATUS_CODES.items():
        method, path = label.split(" ", 1)
        operation = paths.get(path, {}).get(method.lower())
        assert operation is not None, f"{label} is not in the schema: update the known gaps"
        documented = {int(code) for code in operation["responses"]}
        assert not codes & documented, f"{label} now documents {codes & documented}: drop the gap"


def validate(case: Case[Any], response: Response, headers: dict[str, str] | None = None) -> None:
    known_gap = response.status_code in UNDOCUMENTED_STATUS_CODES.get(case.operation.label, ())
    case.validate_response(
        response,
        checks=CHECKS,
        excluded_checks=[status_code_conformance] if known_gap else [],
        headers=headers,
    )
