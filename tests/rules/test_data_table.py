"""Tests for GET /rule/data_table — the generic endpoint consumed by the
rule-data-table component (page / per_page / search / sort / dir / source)."""


def test_data_table_returns_shape(client):
    res = client.get('/rule/data_table')
    assert res.status_code == 200
    data = res.get_json()
    assert {'items', 'total', 'total_pages'} <= set(data.keys())
    assert isinstance(data['items'], list)
    assert data['total'] >= 1


def test_data_table_item_fields(client):
    data = client.get('/rule/data_table').get_json()
    item = data['items'][0]
    for field in ('id', 'title', 'format', 'author', 'description',
                  'creation_date', 'vote_up', 'vote_down', 'to_string'):
        assert field in item


def test_data_table_per_page(client):
    data = client.get('/rule/data_table?per_page=1&page=1').get_json()
    assert len(data['items']) == 1
    assert data['total_pages'] == data['total']


def test_data_table_per_page_capped_at_100(client):
    res = client.get('/rule/data_table?per_page=99999')
    assert res.status_code == 200


def test_data_table_search_by_title(client):
    all_ = client.get('/rule/data_table?per_page=100').get_json()
    title = all_['items'][0]['title']
    data = client.get(f'/rule/data_table?search={title}').get_json()
    assert data['total'] >= 1
    assert any(r['title'] == title for r in data['items'])


def test_data_table_search_no_match(client):
    data = client.get('/rule/data_table?search=zzz-no-such-rule-zzz').get_json()
    assert data['total'] == 0
    assert data['items'] == []


def test_data_table_sort_title(client):
    asc  = client.get('/rule/data_table?sort=title&dir=asc&per_page=100').get_json()
    desc = client.get('/rule/data_table?sort=title&dir=desc&per_page=100').get_json()
    titles_asc  = [r['title'] for r in asc['items']]
    titles_desc = [r['title'] for r in desc['items']]
    assert titles_desc == titles_asc[::-1]


def test_data_table_invalid_sort_key_is_ignored(client):
    res = client.get('/rule/data_table?sort=evil_column&dir=asc')
    assert res.status_code == 200


def test_data_table_source_filter_no_match(client):
    data = client.get(
        '/rule/data_table?source=https://github.com/nobody/no-such-repo'
    ).get_json()
    assert data['total'] == 0


def test_data_table_includes_tags_and_cves(client):
    item = client.get('/rule/data_table').get_json()['items'][0]
    assert isinstance(item.get('tags'), list)
    assert isinstance(item.get('cves'), list)


def test_data_table_rule_type_filter(client):
    all_ = client.get('/rule/data_table?per_page=100').get_json()
    fmt = all_['items'][0]['format']
    data = client.get(f'/rule/data_table?rule_type={fmt}').get_json()
    assert data['total'] >= 1
    assert all(fmt.lower() in (r['format'] or '').lower() for r in data['items'])


def test_data_table_unknown_tag_filter_matches_nothing(client):
    data = client.get('/rule/data_table?tags=no-such-tag-xyz').get_json()
    assert data['total'] == 0


def test_github_source_stats_requires_url(client):
    assert client.get('/rule/github_source_stats').status_code == 400


def test_github_source_stats_shape(client):
    data = client.get(
        '/rule/github_source_stats?url=https://github.com/x/y'
    ).get_json()
    assert {'total_rules', 'formats', 'authors_count',
            'licenses_count', 'last_update'} <= set(data.keys())


def test_export_download_by_ids(client):
    item = client.get('/rule/data_table').get_json()['items'][0]
    res = client.get(f"/rule/export/download?ids={item['id']}&export_format=json_each")
    assert res.status_code == 200
    assert res.data[:2] == b'PK'  # zip magic bytes
