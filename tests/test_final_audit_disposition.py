import json
from pathlib import Path
from types import SimpleNamespace

from swepro_trans.validation import final_audit


def test_published_bundle_cannot_pass_after_independent_audit_rejects_it(tmp_path: Path, monkeypatch) -> None:
    run = tmp_path / "run"
    attempt = run / "attempts" / "attempt_001"
    original = tmp_path / "original"
    (attempt / "intermediate/control").mkdir(parents=True)
    (attempt / "review").mkdir()
    (original / "tests").mkdir(parents=True)
    (original / "tests/config.json").write_text('{"fail_to_pass": []}\n')
    (attempt / "intermediate/control/state.json").write_text(json.dumps({"status": "audit_rejected"}))
    (attempt / "review/independent_audit.json").write_text(json.dumps({"status": "FAIL"}))
    monkeypatch.setattr(final_audit, "resolve_task", lambda _root: SimpleNamespace(
        run_root=run, original=original, instance_id="example",
    ))
    monkeypatch.setattr(final_audit, "latest_attempt", lambda _root: attempt)

    result = final_audit.audit_task(run)
    assert result["status"] == "FAIL"
    assert result["checks"]["attempt_status"] == "audit_rejected"
    assert result["checks"]["independent_audit"] == "FAIL"
    assert "latest attempt is not certified accepted" in result["errors"]
    assert "independent audit rejected this published revision" in result["errors"]
