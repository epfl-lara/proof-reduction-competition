import json
from pathlib import Path

import pytest

import codex_proposal
import report_codex_baselines as reporting
import run_codex_baselines as benchmark
from run_astra_low import CONDITIONS, PARENT, cohort_context, prepare, worklist


def test_added_cohort_preserves_parent_on_exception():
    previous = codex_proposal.MODELS, benchmark.CONDITIONS, reporting.CONDITIONS
    with pytest.raises(RuntimeError):
        with cohort_context():
            assert 'low' in codex_proposal.MODELS['gpt-6-astra']
            assert benchmark.CONDITIONS == reporting.CONDITIONS == CONDITIONS
            raise RuntimeError('simulate interruption')
    assert (codex_proposal.MODELS, benchmark.CONDITIONS, reporting.CONDITIONS) == previous
    assert 'low' not in codex_proposal.MODELS['gpt-6-astra']


def test_only_requested_low_cells_and_parent_order():
    names = ['first', 'second', 'third']
    items = worklist(names, ['second'])
    assert items == [('second', 'gpt-6-astra', 'low', 'original'),
                     ('second', 'gpt-6-astra', 'low', 'deterministic')]
    assert len(worklist(names)) == 6
    with pytest.raises(ValueError, match='Unknown theorem'):
        worklist(names, ['typo'])


def test_resume_keeps_parent_manifest_and_rejects_mutated_cohort(tmp_path, monkeypatch):
    parent_path = PARENT / 'config.json'
    before = parent_path.read_bytes()
    parent = json.loads(before)
    monkeypatch.setattr(codex_proposal, 'cli_identity', lambda: parent['cli'])
    config = prepare(tmp_path)
    assert config['conditions'] == [list(c) for c in CONDITIONS]
    assert config['names'] == parent['names']
    assert config['input_sha256'] == parent['input_sha256']
    assert config['dataset_sha256'] == parent['dataset_sha256']
    assert config['max_repair_rounds'] == parent['max_repair_rounds'] == 3
    assert prepare(tmp_path) == config
    assert parent_path.read_bytes() == before
    changed = {**config, 'workers': 99}
    (tmp_path / 'config.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='configuration changed'):
        prepare(tmp_path)
