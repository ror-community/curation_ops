from unittest.mock import Mock

import httpx
import pytest

import prioritize


@pytest.fixture
def issue():
    issue = Mock(
        number=123,
        title="Modify the information: Example organization",
        body="ROR ID: https://ror.org/012345678\nDescription of change: Update the website",
    )
    issue.get_labels.return_value = []
    return issue


@pytest.fixture
def mock_api(monkeypatch):
    client_class = httpx.Client

    def configure(ror_response=None, affiliation_count=0):
        requests = []

        def handle_request(request):
            requests.append(request)
            if request.url.host == "api.ror.org":
                assert request.url.path == "/v2/organizations/012345678"
                if isinstance(ror_response, Exception):
                    raise ror_response
                assert ror_response is not None, "Unexpected ROR lookup"
                return ror_response
            assert request.url.host == "api.openalex.org"
            assert request.url.path == "/works"
            return httpx.Response(200, json={"meta": {"count": affiliation_count}})

        transport = httpx.MockTransport(handle_request)
        monkeypatch.setattr(
            prioritize.httpx,
            "Client",
            lambda **kwargs: client_class(transport=transport, **kwargs),
        )
        return requests

    return configure


@pytest.mark.parametrize("ror_id", ["012345678", "https://ror.org/012345678"])
@pytest.mark.parametrize("types", [["funder"], ["education", "funder"]])
def test_funder_update_is_p1_without_affiliation_lookup(issue, mock_api, ror_id, types):
    requests = mock_api(httpx.Response(200, json={"types": types}))

    priority = prioritize.prioritize_issue(issue, "update record", ror_id=ror_id)

    assert priority == "P1"
    issue.add_to_labels.assert_called_once_with("P1", "update record")
    assert [request.url.host for request in requests] == ["api.ror.org"]


@pytest.mark.parametrize("types", [["education"], ["government"], []])
@pytest.mark.parametrize("affiliation_count, expected", [(0, "P2"), (100, "P1")])
def test_other_updates_keep_affiliation_priority(
    issue, mock_api, types, affiliation_count, expected
):
    requests = mock_api(
        httpx.Response(200, json={"types": types}), affiliation_count=affiliation_count
    )

    priority = prioritize.prioritize_issue(
        issue, "update record", ror_id="https://ror.org/012345678"
    )

    assert priority == expected
    issue.add_to_labels.assert_called_once_with(expected, "update record")
    assert [request.url.host for request in requests] == [
        "api.ror.org", "api.openalex.org"
    ]


@pytest.mark.parametrize(
    "ror_response",
    [
        httpx.Response(404),
        httpx.Response(429),
        httpx.Response(500),
        httpx.Response(200, content="invalid JSON"),
        httpx.Response(200, json={}),
        httpx.ReadTimeout("ROR lookup timed out"),
    ],
)
def test_ror_lookup_failure_falls_back_to_affiliation_priority(issue, mock_api, ror_response):
    requests = mock_api(ror_response, affiliation_count=100)

    priority = prioritize.prioritize_issue(
        issue, "update record", ror_id="https://ror.org/012345678"
    )

    assert priority == "P1"
    issue.add_to_labels.assert_called_once_with("P1", "update record")
    assert [request.url.host for request in requests] == [
        "api.ror.org", "api.openalex.org"
    ]


def test_update_without_ror_id_keeps_default_priority(issue, mock_api):
    requests = mock_api()

    assert prioritize.prioritize_issue(issue, "update record") == "P2"
    issue.add_to_labels.assert_called_once_with("P2", "update record")
    assert requests == []


def test_new_record_uses_affiliations_without_ror_lookup(issue, mock_api):
    requests = mock_api()

    assert prioritize.prioritize_issue(issue, "new record", name="Example") == "P3"
    issue.add_to_labels.assert_called_once_with("P3", "new record")
    assert [request.url.host for request in requests] == ["api.openalex.org"]


@pytest.mark.parametrize("org_type", ["Funder", "Government"])
def test_body_type_still_assigns_p1_without_lookup(issue, mock_api, org_type):
    requests = mock_api()
    issue.body = f"Organization type: {org_type}\n"

    assert prioritize.prioritize_issue(issue, "new record", name="Example") == "P1"
    issue.add_to_labels.assert_called_once_with("P1", "new record")
    assert requests == []


def test_existing_priority_is_preserved(issue, mock_api):
    requests = mock_api()
    label = Mock()
    label.name = "P2"
    issue.get_labels.return_value = [label]

    assert prioritize.prioritize_issue(issue, "update record", ror_id="012345678") is None
    issue.add_to_labels.assert_not_called()
    assert requests == []


def test_merge_still_assigns_p1_without_lookup(issue, mock_api):
    requests = mock_api()
    issue.title = "Merge two records"

    assert prioritize.prioritize_issue(issue) == "P1"
    issue.add_to_labels.assert_called_once_with("P1", "merge records")
    assert requests == []
