import copy

from scripts.learning_training_gate import decision
from scripts.prepare_training_data import MINIMUMS


def state():
    return {'schema': 'learning-autopilot.v1', 'phase': 'ready_for_training',
            'counts': dict(MINIMUMS), 'errors': [], 'training_started': False,
            'training_requirements': {
                'independently_reviewed_train': True, 'registered_validation': True,
                'registered_test': True, 'matched_baseline_evaluation': True,
                'rollback_plan': True, 'trainer_integration': True}}


def test_complete_snapshot_is_eligible_without_starting_any_process():
    result = decision(state())
    assert result == {'eligible': True, 'reasons': [], 'action': 'invoke_isolated_trainer'}


def test_current_partial_intake_is_refused_for_every_missing_gate():
    current = state(); current['phase'] = 'collecting_reviewed_data'; current['counts'] = {'train': 73, 'validation': 0, 'test': 0}
    current['training_requirements'] = {'independently_reviewed_train': False, 'registered_validation': False,
                                        'registered_test': False, 'matched_baseline_evaluation': False,
                                        'rollback_plan': False, 'trainer_integration': False}
    result = decision(current)
    assert result['eligible'] is False and result['action'] == 'continue_reviewed_intake'
    assert set(result['reasons']) == {
        'train_minimum_not_met', 'validation_minimum_not_met', 'test_minimum_not_met',
        'intake_not_marked_ready_for_training', 'independently_reviewed_train_missing',
        'registered_validation_missing', 'registered_test_missing',
        'matched_baseline_evaluation_missing', 'rollback_plan_missing',
        'trainer_integration_missing'}


def test_errors_or_started_snapshot_can_never_become_eligible():
    current = state(); current['errors'] = [{'detail': 'fixture'}]
    assert 'intake_errors_present' in decision(current)['reasons']
    current = state(); current['training_started'] = True
    assert 'training_already_started_in_snapshot' in decision(current)['reasons']


def test_complete_data_without_registered_trainer_is_refused():
    current = state()
    current['training_requirements']['trainer_integration'] = False
    result = decision(current)
    assert result == {
        'eligible': False,
        'reasons': ['trainer_integration_missing'],
        'action': 'continue_reviewed_intake',
    }
