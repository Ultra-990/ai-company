import pytest
import json
from scripts.check_vision_training_inputs import completion_labels


def test_candidate_images_cannot_escape_bundle_even_with_matching_hash(tmp_path,monkeypatch):
    from scripts import vector_school
    from scripts.check_vision_training_inputs import candidate_image
    from hashlib import sha256
    monkeypatch.setattr(vector_school,'ROOT',tmp_path)
    monkeypatch.setattr('scripts.check_vision_training_inputs.BUNDLE_ROOTS',(tmp_path,))
    out=tmp_path/'bundle';out.mkdir();(out/'images').mkdir()
    private=tmp_path/'outside.png';private.write_bytes(b'fixture')
    digest=sha256(private.read_bytes()).hexdigest()
    image={'sha256':digest,'file':'../outside.png'}
    with pytest.raises(ValueError):candidate_image(out,image)
    image['file']='images/'+digest+'.png'
    (out/image['file']).symlink_to(private)
    with pytest.raises(ValueError):candidate_image(out,image)


def test_image_and_instruction_tokens_never_become_learning_targets():
    assert completion_labels([1,9,9,2,3,4,7],[1,9,9,2],9,2,7,20)==[-100,-100,-100,-100,3,4,7]


@pytest.mark.parametrize('ids,prefix,expected,eos,limit',[
    ([1,9,2,3,7],[1,9,2],1,7,4),  # Never truncate an otherwise valid example.
    ([1,9,2,3,7],[1,2,9],1,7,20),
    ([1,9,2,9,7],[1,9,2],2,7,20), # No image tokens in the assistant target.
    ([1,9,2,3,7],[1,9,2],2,7,20), # Grid expects another image token.
    ([1,9,2,3,4],[1,9,2],1,7,20),
    ([1,2,3,7],[1,2],0,7,20),
])
def test_invalid_multimodal_boundaries_fail(ids,prefix,expected,eos,limit):
    with pytest.raises(ValueError):completion_labels(ids,prefix,9,expected,eos,limit)


@pytest.mark.parametrize('change',[{'max_steps':4},{'vision_layers_frozen':False},{'learning_rate':.01}])
def test_input_training_protocol_cannot_silently_expand(tmp_path,monkeypatch,change):
    from scripts import train_vision_input_pilot as pilot
    plan=pilot.load_protocol();plan['training'].update(change)
    path=tmp_path/'protocol.json';path.write_text(json.dumps(plan));monkeypatch.setattr(pilot,'PLAN',path)
    with pytest.raises(ValueError):pilot.load_protocol()


def test_text_conversion_registry_restored_on_failed_full_model_load():
    from types import SimpleNamespace
    from scripts.train_vision_input_pilot import full_vision_names
    previous=[SimpleNamespace(source_patterns=['^model.language_model'],target_patterns=['model'])]
    class Registry:
        mapping=previous
        def get_checkpoint_conversion_mapping(self,name):return self.mapping
        def register_checkpoint_conversion_mapping(self,name,mapping,overwrite):self.mapping=mapping
    registry=Registry()
    with pytest.raises(RuntimeError):
        with full_vision_names(registry):
            assert registry.mapping==[]
            raise RuntimeError('Failed fixture load')
    assert registry.mapping is previous
    registry.mapping=[]
    with pytest.raises(ValueError):
        with full_vision_names(registry):pytest.fail('Unexpected mapping must not be changed')
