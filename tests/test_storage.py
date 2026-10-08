from app.kb.storage import Store


def test_run_lifecycle(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    run_id = store.create_run("тема", "бренд")
    store.update_run(run_id, research={"topic": "тема"}, score=77.0, status="researched")

    run = store.get_run(run_id)
    assert run["status"] == "researched"
    assert run["research"]["topic"] == "тема"
    assert run["score"] == 77.0


def test_knowledge_and_metrics(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    run_id = store.create_run("двери")
    store.save_knowledge(run_id, "двери", "5 ошибок при выборе", 90)
    store.save_knowledge(run_id, "двери", "что скрывают продавцы", 70)
    best = store.best_knowledge(limit=5)
    assert best[0]["score"] == 90

    store.save_metrics(run_id, "telegram", "p1", {"views": 100, "likes": 5, "comments": 1, "ctr": 3.2})
    assert store.avg_ctr() == 3.2


def test_steps_logged(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    run_id = store.create_run("x")
    store.save_step(run_id, "research", 12, True)
    steps = store.get_steps(run_id)
    assert steps[0]["agent"] == "research"
    assert steps[0]["ok"] == 1
