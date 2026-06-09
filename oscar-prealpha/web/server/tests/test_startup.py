def test_startup_loads_fixture_without_recompute(monkeypatch):
    called = {"build": False}

    import build_snapshot

    def _boom():
        called["build"] = True
        raise AssertionError("should not recompute")

    monkeypatch.setattr(build_snapshot, "build", _boom)
    import main

    main._startup()
    assert main.SNAPSHOT.get("meta", {}).get("app") == "OSCAR"
    assert called["build"] is False
