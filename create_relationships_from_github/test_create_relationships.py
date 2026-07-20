import csv

import pytest

import create_relationships
from create_relationships import (
    extract_relationships,
    flag_circular_relationships,
    RelationshipRow,
)

ID_A = 'https://ror.org/028rfb880'
ID_B = 'https://ror.org/03bqy0f38'
ID_C = 'https://ror.org/05xyz1234'


def _row(record_id, related_id, rel_type, location='Release'):
    return RelationshipRow('1', 'url', 'title', 'name', record_id,
                           related_id, 'related_name', rel_type, location)


def _write_input_csv(path, ids_and_names):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'names.types.ror_display'])
        for ror_id, name in ids_and_names:
            writer.writerow([ror_id, name])


def _field(csv_row, attr):
    return csv_row[RelationshipRow.FIELD_LABELS[attr]]


def _read_output_rows(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def test_helper_flags_parent_child_contradiction():
    rows = [
        _row(ID_A, ID_B, 'Parent'),
        _row(ID_A, ID_B, 'Child'),
        _row(ID_A, ID_C, 'Parent'),
    ]
    flag_circular_relationships(rows)
    assert rows[0].rel_type == 'Error'
    assert rows[1].rel_type == 'Error'
    assert rows[2].rel_type == 'Parent'
    assert rows[0].location == 'Release'


def test_helper_flags_successor_predecessor_contradiction():
    rows = [
        _row(ID_A, ID_B, 'Successor'),
        _row(ID_A, ID_B, 'Predecessor'),
    ]
    flag_circular_relationships(rows)
    assert rows[0].rel_type == 'Error'
    assert rows[1].rel_type == 'Error'


def test_helper_ignores_missing_ids():
    rows = [
        _row('', ID_B, 'Parent'),
        _row('', ID_B, 'Child'),
    ]
    flag_circular_relationships(rows)
    assert rows[0].rel_type == 'Parent'
    assert rows[1].rel_type == 'Child'


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError('network call attempted')
    monkeypatch.setattr(create_relationships, 'get_ror_name', _boom)


def _issue(number, record_id, name, rel_lines, description=''):
    body = f'ROR ID: {record_id}\nName of organization: {name}\n'
    if description:
        body += f'Description of change: {description}\n'
    body += 'Related organizations: ' + ' '.join(
        f'{rid} ({rtype})' for rid, rtype in rel_lines) + '\n'
    return {
        'number': number,
        'title': f'Issue {number}',
        'url': f'https://github.com/ror-community/ror-updates/issues/{number}',
        'body': body,
    }


def test_within_issue_contradiction(tmp_path):
    input_csv = tmp_path / 'input.csv'
    output_csv = tmp_path / 'output.csv'
    _write_input_csv(input_csv, [(ID_A, 'Org A'), (ID_B, 'Org B'), (ID_C, 'Org C')])

    contradiction = _issue(101, ID_A, 'Org A',
                           [(ID_B, 'child'), (ID_B, 'parent')])
    control = _issue(102, ID_A, 'Org A', [(ID_C, 'parent')])

    extract_relationships([contradiction, control], str(input_csv), str(output_csv))
    rows = _read_output_rows(str(output_csv))

    ab_pairs = {(ID_A, ID_B), (ID_B, ID_A)}
    flagged = [r for r in rows if (_field(r, 'record_id'), _field(r, 'related_id')) in ab_pairs]
    assert len(flagged) == 4
    assert all(_field(r, 'rel_type') == 'Error' for r in flagged)
    assert all(_field(r, 'location') == 'Release' for r in flagged)

    control_pairs = {(ID_A, ID_C), (ID_C, ID_A)}
    control_rows = [r for r in rows if (_field(r, 'record_id'), _field(r, 'related_id')) in control_pairs]
    types = sorted(_field(r, 'rel_type') for r in control_rows)
    assert types == ['Child', 'Parent']


def test_cross_issue_cycle(tmp_path):
    input_csv = tmp_path / 'input.csv'
    output_csv = tmp_path / 'output.csv'
    _write_input_csv(input_csv, [(ID_A, 'Org A'), (ID_B, 'Org B')])

    issue_a = _issue(101, ID_A, 'Org A', [(ID_B, 'parent')])
    issue_b = _issue(201, ID_B, 'Org B', [(ID_A, 'parent')])

    extract_relationships([issue_a, issue_b], str(input_csv), str(output_csv))
    rows = _read_output_rows(str(output_csv))

    ab_pairs = {(ID_A, ID_B), (ID_B, ID_A)}
    flagged = [r for r in rows if (_field(r, 'record_id'), _field(r, 'related_id')) in ab_pairs]
    assert len(flagged) == 4
    assert all(_field(r, 'rel_type') == 'Error' for r in flagged)


ZERO_WIDTH_SPACE = '\u200b'


def test_name_with_zero_width_char_still_resolves_ror_id(tmp_path):
    """A new record's name carrying an invisible character must still match.

    Names pasted into GitHub issues sometimes carry a zero-width space. When
    the issue has no ROR ID yet (a new record), the ID is looked up by name;
    an unmatched name silently yields an empty Record ID.
    """
    input_csv = tmp_path / 'input.csv'
    output_csv = tmp_path / 'output.csv'
    _write_input_csv(input_csv, [(ID_A, 'Org A*en'), (ID_B, 'Org B*en')])

    issue = _issue(101, '', ZERO_WIDTH_SPACE + 'Org A', [(ID_B, 'parent')])

    extract_relationships([issue], str(input_csv), str(output_csv))
    rows = _read_output_rows(str(output_csv))

    forward = [r for r in rows if _field(r, 'related_id') == ID_B]
    assert forward, 'expected a row relating the new record to ID_B'
    assert _field(forward[0], 'record_id') == ID_A

    inverse = [r for r in rows if _field(r, 'record_id') == ID_B]
    assert inverse, 'expected the inverse row'
    assert _field(inverse[0], 'related_id') == ID_A


def test_zero_width_char_not_written_to_output(tmp_path):
    input_csv = tmp_path / 'input.csv'
    output_csv = tmp_path / 'output.csv'
    _write_input_csv(input_csv, [(ID_A, 'Org A*en'), (ID_B, 'Org B*en')])

    issue = _issue(101, '', ZERO_WIDTH_SPACE + 'Org A', [(ID_B, 'parent')])

    extract_relationships([issue], str(input_csv), str(output_csv))

    with open(output_csv, encoding='utf-8') as f:
        assert ZERO_WIDTH_SPACE not in f.read()


def test_declarations_outside_related_organizations_are_ignored(tmp_path):
    """Only the 'Related organizations:' field declares relationships.

    Free-text fields often restate a relationship informally. Parsing the
    whole issue body treats that prose as an authoritative declaration.
    """
    input_csv = tmp_path / 'input.csv'
    output_csv = tmp_path / 'output.csv'
    _write_input_csv(input_csv, [(ID_A, 'Org A'), (ID_B, 'Org B')])

    issue = _issue(101, ID_A, 'Org A', [(ID_B, 'successor-np')],
                   description=f'Add relationship: {ID_B} (parent)')

    extract_relationships([issue], str(input_csv), str(output_csv))
    rows = _read_output_rows(str(output_csv))

    assert sorted(_field(r, 'rel_type') for r in rows) == ['Successor']


def test_prose_delete_does_not_resurrect_deleted_relationship(tmp_path):
    input_csv = tmp_path / 'input.csv'
    output_csv = tmp_path / 'output.csv'
    _write_input_csv(input_csv, [(ID_A, 'Org A'), (ID_B, 'Org B')])

    issue = _issue(101, ID_A, 'Org A', [(ID_B, 'delete')],
                   description=f'Remove relationship: {ID_B} (related)')

    extract_relationships([issue], str(input_csv), str(output_csv))
    rows = _read_output_rows(str(output_csv))

    assert sorted(_field(r, 'rel_type') for r in rows) == ['Delete', 'Delete']
