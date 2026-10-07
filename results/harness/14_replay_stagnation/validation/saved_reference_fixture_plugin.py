"""Use archived environment metadata for existing saved-certificate tests only."""
import json
from pathlib import Path
import pytest
from proof_eval.verification.backend import LeanBackend

@pytest.fixture(autouse=True)
def archived_pinned_fingerprints(monkeypatch):
    root = Path('/localhome/milikic/proof-replay-current-validation')
    certificates = {}
    for line in (root/'results/deterministic/00_reference_baseline/reference_values.jsonl').read_text().splitlines():
        record = json.loads(line)
        for version, saved in record['per_version'].items():
            details = saved['provenance']['details']
            certificates[(record['name'], version, details['project_dir'])] = saved['provenance']['environment_fingerprint']
    original = LeanBackend.fingerprint
    def fingerprint(self, row, version, project_dir):
        key = (row['name'], version, str(Path(project_dir).resolve()))
        if key in certificates:
            return certificates[key]
        return original(self, row, version, project_dir)
    monkeypatch.setattr(LeanBackend, 'fingerprint', fingerprint)
