import json

from scripts import learning_trainer_runner as runner


def state(tmp_path, **requirements):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({
        'schema': 'learning-autopilot.v1', 'phase': 'collecting_reviewed_data',
        'counts': {'train': 1, 'validation': 0, 'test': 0}, 'errors': [],
        'training_started': False, 'entries': {},
        'training_requirements': requirements,
    }))
    return path


def test_refuses_before_gate_and_never_starts(tmp_path):
    state_path = state(tmp_path)
    exam = tmp_path / 'exam.json'; exam.write_text('{}')
    result = runner.invoke(state_path, exam)
    assert result['status'] == 'refused_by_gate'
    assert result['training_started'] is False
    assert result['automatic_promotion'] is False


def test_eligible_planning_records_exact_trainer_command(tmp_path, monkeypatch):
    requirements = {key: True for key in (
        'independently_reviewed_train', 'registered_validation', 'registered_test',
        'matched_baseline_evaluation', 'rollback_plan', 'trainer_integration')}
    path = state(tmp_path, **requirements)
    data = json.loads(path.read_text()); data.update(
        phase='ready_for_training', counts={'train': 200, 'validation': 25, 'test': 50})
    path.write_text(json.dumps(data))
    exam = tmp_path / 'exam.json'; exam.write_text('{}')
    monkeypatch.setattr(runner, 'TRAINER', tmp_path / 'trainer.py')
    runner.TRAINER.write_text('# trainer')
    result = runner.invoke(path, exam)
    assert result['status'] == 'ready_to_invoke'
    assert result['training_started'] is False
    assert result['command'][-1] == '--run'
    assert result['automatic_promotion'] is False
