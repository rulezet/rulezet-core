"""Night shift (/nightshift): every case is solvable by its reference rule,
the browser never receives the answers, and the score is decided server-side."""
import json
import uuid

from app.features.nightshift import nightshift_core as NightshiftModel


def test_every_case_is_solvable_by_its_reference_rule(app):
    with app.app_context():
        for case in NightshiftModel.list_cases():
            rule, error = NightshiftModel.build_rule(case, case['rule']['reference'])
            assert error is None, case['id']
            samples = [s for g in ('malicious', 'benign', 'hidden_variants') for s in case['corpus'][g]]
            results, error = NightshiftModel.evaluate(rule, samples)
            assert error is None, (case['id'], error)
            for s in case['corpus']['malicious'] + case['corpus']['hidden_variants']:
                assert results[s['id']], (case['id'], s['id'], 'should match')
            for s in case['corpus']['benign']:
                assert not results[s['id']], (case['id'], s['id'], 'false positive')
            for key in case['evidence']['required']:
                assert NightshiftModel._is_valid_pin(case, key), (case['id'], key)


def test_public_case_hides_the_answers(app):
    with app.app_context():
        for case in NightshiftModel.list_cases():
            public = json.dumps(NightshiftModel.public_case(case))
            assert '"reference"' not in public      # the key, not the word (setup.ps1's $ErrorActionPreference)
            for v in case['corpus']['hidden_variants']:
                assert v['id'] not in public and v['name'] not in public


def test_case_loop_and_server_side_score(client):
    player = str(uuid.uuid4())
    run = client.post('/nightshift/case/start', json={'player': player, 'case': '1-invoice'}).get_json()['run']
    blanks = {'a': 'AutoOpen', 'b': 'DownloadString', 'condition': '$a and $b'}

    # Deploy refused until the key evidence is pinned
    res = client.post('/nightshift/case/deploy', json={'player': player, 'run': run['uuid'], 'blanks': blanks}).get_json()
    assert res['outcome'] == 'need_evidence'

    # Another browser can't touch this run
    assert client.post('/nightshift/case/hint', json={'player': str(uuid.uuid4()), 'run': run['uuid']}).status_code == 404

    # A blank can't break out of its string
    res = client.post('/nightshift/case/test', json={'player': player, 'run': run['uuid'],
                      'blanks': {'a': 'x"\n condition: true }', 'b': 'y', 'condition': '$a'}})
    assert res.status_code == 400

    for key in ('file:invoice_0923.docm', 'log:proc-powershell'):
        assert client.post('/nightshift/case/pin', json={'player': player, 'run': run['uuid'], 'key': key}).status_code == 200
    assert client.post('/nightshift/case/pin', json={'player': player, 'run': run['uuid'], 'key': 'line:var-1:0'}).status_code == 400

    res = client.post('/nightshift/case/deploy', json={'player': player, 'run': run['uuid'], 'blanks': blanks}).get_json()
    assert res['outcome'] == 'closed'
    assert res['run']['stars'] == 3 and res['run']['score'] > 0
    assert res['variants'][0]['matched']
