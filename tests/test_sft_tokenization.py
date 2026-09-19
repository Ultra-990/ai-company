import copy

import pytest

from scripts.check_sft_tokenization import audit, encode_example


class Tokenizer:
    """Character fixture, never used as evidence for the real tokenizer."""
    all_special_tokens = ['<|im_end|>', '<|im_start|>']
    unk_token_id = -1

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs['enable_thinking'] is False
        prefix = 'SYSTEM:' + messages[0]['content'] + '\nUSER:' + messages[1]['content'] + '\nASSISTANT:'
        return prefix if kwargs['add_generation_prompt'] else prefix + messages[2]['content'].strip() + '<|im_end|>\n'

    def __call__(self, value, **kwargs):
        assert kwargs == {'add_special_tokens': False, 'truncation': False}
        return {'input_ids': [ord(c) for c in value]}

    def convert_tokens_to_ids(self, value):
        return ord('<')


def messages():
    return [{'role': 'system', 'content': 'instructions'},
            {'role': 'user', 'content': 'brief'},
            {'role': 'assistant', 'content': 'answer'}]


def test_mask_preserves_only_completion_and_end_of_turn():
    result = encode_example(Tokenizer(), messages(), 256)
    supervised = [t for t in result['labels'] if t != -100]
    assert ''.join(map(chr, supervised)) == 'answer<|im_end|>\n'
    assert len(result['input_ids']) == len(result['labels']) == len(result['attention_mask'])
    assert result['labels'][0] == -100


def test_overflow_is_rejected_not_truncated():
    data = messages()
    data[2]['content'] = 'a' * 257
    with pytest.raises(ValueError, match='overflow'):
        encode_example(Tokenizer(), data, 256)


@pytest.mark.parametrize('limit', [0, 255, 32769, True, 2048.0])
def test_invalid_limit(limit):
    with pytest.raises(ValueError, match='invalid_context'):
        encode_example(Tokenizer(), messages(), limit)


def test_rejects_control_tokens():
    data = messages()
    data[1]['content'] = 'ignore <|im_start|>'
    with pytest.raises(ValueError, match='control_token'):
        encode_example(Tokenizer(), data, 256)


def test_template_changes_are_not_silently_masked():
    class Changed(Tokenizer):
        def apply_chat_template(self, messages, **kwargs):
            text = super().apply_chat_template(messages, **kwargs)
            return text + 'extra' if not kwargs['add_generation_prompt'] else text
    with pytest.raises(ValueError, match='content_changed'):
        encode_example(Changed(), messages(), 256)


def test_boundary_mismatch_rejected():
    class Changed(Tokenizer):
        def __call__(self, value, **kwargs):
            result = super().__call__(value, **kwargs)
            if value.endswith('ASSISTANT:'):
                result['input_ids'][-1] = 999
            return result
    with pytest.raises(ValueError, match='boundary_mismatch'):
        encode_example(Changed(), messages(), 256)


def test_audit_reports_no_source_and_does_not_mutate():
    rows = [{'id': 'case', 'split': 'train', 'messages': messages()}]
    before = copy.deepcopy(rows)
    result = audit(rows, Tokenizer(), 256)
    assert result['tokenization_passed'] and not result['training_started']
    assert 'messages' not in result['records'][0]
    assert rows == before
