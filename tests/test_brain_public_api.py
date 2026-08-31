from app.brain import Brain, BrainDecision, BrainTask


def test_brain_public_exports_are_available():
    brain = Brain()

    decision = brain.decide(
        title="Test",
        rationale="Test kontraktu",
        requires_approval=True,
    )

    assert isinstance(decision, BrainDecision)
    assert decision.requires_approval is True
    assert len(brain.decisions) == 1


def test_brain_task_is_reported_as_pending():
    brain = Brain()
    task = BrainTask(id="task-1", title="Testowe zadanie")

    brain.add_task(task)

    report = brain.report()

    assert report["tasks_count"] == 1
    assert report["decisions_count"] == 0
    assert report["pending_tasks"] == [task]
