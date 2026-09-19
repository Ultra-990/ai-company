from app.services.ui_interaction_contract import UI_INTERACTION_CONTRACT
from app.services.multifile_generation import INSTRUCTION as CODE_INSTRUCTION
from scripts.draft_web_design_training import INSTRUCTION as PLAN_INSTRUCTION


def test_planner_and_code_generator_receive_the_same_interaction_contract():
    assert UI_INTERACTION_CONTRACT in CODE_INSTRUCTION
    assert UI_INTERACTION_CONTRACT in PLAN_INSTRUCTION
    for rule in ('Menu button:', 'Navigation link:', 'Media card:', 'Scroll scene:',
                 'Video:', 'Back:', 'pointer-events:none', 'reduced motion',
                 'independent browser', 'No parent escape'):
        assert rule in UI_INTERACTION_CONTRACT
    assert 'within the agreed scope' in UI_INTERACTION_CONTRACT
    assert 'never claim they passed' in UI_INTERACTION_CONTRACT
    assert 'first-time visitor journey' in UI_INTERACTION_CONTRACT
    assert 'avoid dead ends' in UI_INTERACTION_CONTRACT
