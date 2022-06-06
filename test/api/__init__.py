from datetime import datetime, timedelta, timezone
from enum import Enum

from odp import ODPScope


class ProviderAuth(Enum):
    """API routes that support provider-specific resource authorization
    may have three possible outcomes (all else being equal) depending on
    whether the test client is configured with no provider, or with a
    provider (not) matching the resource provider."""
    NONE = 0
    MATCH = 1
    MISMATCH = 2


all_scopes = [s for s in ODPScope]


def all_scopes_excluding(scope):
    return [s for s in ODPScope if s != scope]


def assert_empty_result(response):
    assert response.status_code == 200
    assert response.json() is None


def assert_forbidden(response):
    assert response.status_code == 403
    assert response.json() == {'detail': 'Forbidden'}


def assert_not_found(response):
    assert response.status_code == 404
    assert response.json() == {'detail': 'Not Found'}


def assert_method_not_allowed(response):
    assert response.status_code == 405
    assert response.json() == {'detail': 'Method Not Allowed'}


def assert_conflict(response, message):
    assert response.status_code == 409
    assert response.json() == {'detail': message}


def assert_unprocessable(response, message):
    assert response.status_code == 422
    assert response.json() == {'detail': message}


def assert_new_timestamp(timestamp):
    # 10 minutes is quite lenient, but handy for debugging
    assert datetime.now(timezone.utc) - timedelta(seconds=600) < timestamp < datetime.now(timezone.utc)
