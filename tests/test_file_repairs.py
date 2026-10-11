import json
import pytest
from app.models.artifact import Artifact
from app.models.local_inference import LocalInference
from app.services import application_revisions as revisions,local_inference
from app.services.application_profile import (PROFILE,REPAIR_PROFILE,EXPORTED_TASK_PREFIX,
    assemble_repair,messages_for,parse_sources,repair_base)
from app.services.agent_packets import digest
from app.services.workspace_packages import read_package
from tests.test_application_revisions import generated
from tests.test_local_inference import config_and_no_network,CONFIG
from tests.test_package_runner import FILES


def test_merge_preserves_every_other_file_and_original_mapping():
    base=dict(FILES)
    raw=json.dumps({'changes':{'app.py':'# corrected\nprint(3)'}})
    result,files,changed=assemble_repair(raw,base)
    assert changed==['app.py'] and json.loads(result)['files']==files
    assert {k:v for k,v in files.items() if k!='app.py'}=={k:v for k,v in base.items() if k!='app.py'}
    assert base==FILES


@pytest.mark.parametrize('changes',[{}, {'test_app.py':'altered'}, {'../x':'escape'},
    {'new.py':'new'}, {'app.py':None}, {'app.py':''}, {'app.py':FILES['app.py']},
    {'app.py':'a','index.html':'b','README.md':'c'}, {'app.py':'x'*33000}])
def test_invalid_patch_is_rejected(changes):
    with pytest.raises(ValueError):assemble_repair(json.dumps({'changes':changes}),FILES)


@pytest.mark.parametrize('raw',['{"changes":{"app.py":"a","app.py":"b"}}',
    '{"changes":{},"files":{}}','{"changes":{"app.py":"x"}},','[]'])
def test_invalid_json_contract(raw):
    with pytest.raises(ValueError):assemble_repair(raw,FILES)


def test_base_requires_a_bound_rejected_result():
    content=json.dumps({'files':FILES})
    packet={'revision':{'previous_attempt_id':1,'rejected_result':content,'rejected_checksum':digest(content)}}
    assert repair_base(packet)==FILES
    packet['revision']['rejected_checksum']='0'*64
    with pytest.raises(ValueError):repair_base(packet)


def exported_messages(rejected=None):
    rejected = rejected if rejected is not None else json.dumps({'files':FILES},ensure_ascii=False)
    context={'task_id':7,'project_id':4,'department_id':23,'role':'builder',
        'task_context':{'title':'Plan zajec','brief':'Pelny brief bez skrotow',
                        'completion_criterion':'Dokladny wynik'},
        'accepted_predecessor':None,
        'revision':{'previous_attempt_id':3,'rejection_reason':'Napraw routing i UI.',
                    'rejected_result':rejected,'rejected_checksum':'a'*64}}
    return [{'role':'system','content':'policy'},
            {'role':'user','content':EXPORTED_TASK_PREFIX+json.dumps(context,ensure_ascii=False,indent=2)}],context


def test_repair_prompt_compacts_rejected_sources_losslessly_and_preserves_context():
    messages,context=exported_messages()
    result=messages_for(messages,REPAIR_PROFILE)
    encoded=result[1]['content'];decoded=json.loads(encoded[len(EXPORTED_TASK_PREFIX):])
    assert decoded['revision']['rejected_result']=={'files':FILES}
    assert parse_sources(json.dumps(decoded['revision']['rejected_result'],ensure_ascii=False))==FILES
    expected=context|{'revision':context['revision']|{'rejected_result':{'files':FILES}}}
    assert decoded==expected
    assert result[0]['content'].startswith('policy\nOUTPUT CONTRACT python-web-repair-v1:')
    assert len(encoded.encode())<len(messages[1]['content'].encode())


def test_lossless_encoding_can_cross_context_gate_without_reducing_output_budget():
    sources={name:(value+'\n'+('const marker = "\\\\quoted\\\\";\n'*220))
             for name,value in FILES.items()}
    messages,context=exported_messages(json.dumps({'files':sources},ensure_ascii=False))
    compact=messages_for(messages,REPAIR_PROFILE)
    instruction_bytes=len(compact[0]['content'].encode())
    raw_bytes=instruction_bytes+len(messages[1]['content'].encode())
    compact_bytes=sum(len(item['content'].encode()) for item in compact)
    context_capacity=(raw_bytes+compact_bytes)//2
    assert compact_bytes <= context_capacity < raw_bytes
    # The regression changes prompt representation, not the reserved generation budget.
    num_ctx=context_capacity+4096+1024
    assert compact_bytes <= num_ctx-4096-1024 < raw_bytes
    decoded=json.loads(compact[1]['content'][len(EXPORTED_TASK_PREFIX):])
    assert decoded['revision']['rejected_result']['files']==sources


def test_nonrepair_and_unknown_legacy_user_messages_are_not_reencoded():
    messages,context=exported_messages()
    assert messages_for(messages,'text')==messages
    assert messages_for(messages,PROFILE)[1]==messages[1]
    legacy=[messages[0],{'role':'user','content':'legacy repair context'}]
    assert messages_for(legacy,REPAIR_PROFILE)[1]==legacy[1]


@pytest.mark.parametrize('content',[EXPORTED_TASK_PREFIX+'{',
    EXPORTED_TASK_PREFIX+json.dumps({'revision':None}),
    EXPORTED_TASK_PREFIX+json.dumps({'revision':{'rejected_result':None}}),
    EXPORTED_TASK_PREFIX+json.dumps({'revision':{'rejected_result':'{"files":{}}'}}),
    EXPORTED_TASK_PREFIX+'{"revision":{"rejected_result":"x","rejected_result":"y"}}'])
def test_recognized_broken_repair_context_fails_closed(content):
    with pytest.raises(ValueError):
        messages_for([{'role':'system','content':'policy'},{'role':'user','content':content}],REPAIR_PROFILE)


def test_real_service_keeps_raw_patch_and_assembled_result_separate(client,generated,task_repository):
    raw=json.dumps({'changes':{'README.md':'New instructions, no claim of tested code.'}})
    class Provider:
        def __init__(self,c):assert 'changes' in c['format']['properties']
        def complete(self,m):
            assert REPAIR_PROFILE in m[0]['content']
            return {'content':raw,'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    params=generated[0]|{'auto_test':False}
    with task_repository._session_factory() as s:
        rev=revisions.create(s,output_profile=REPAIR_PROFILE,**params);s.commit()
        with pytest.raises(ValueError):revisions.create(s,**params)
        s.rollback()
        result=revisions.execute(s,rev['id'],Provider,None)
        assert result['state']=='awaiting_review'
        inference=s.get(LocalInference,result['inference_id'])
        assembled=json.loads(inference.result_content)['files']
        assert assembled==FILES|{'README.md':json.loads(raw)['changes']['README.md']}
        metadata=inference.metrics['assembly']
        raw_artifact=s.get(Artifact,metadata['raw_artifact_id'])
        assert raw_artifact.content==raw and raw_artifact.checksum==digest(raw)
        assert metadata['changed_files']==['README.md'] and 'test_app.py' in metadata['preserved_files']
        assert metadata['tests_checksum']==digest(FILES['test_app.py'])
        old,_=read_package(s,params['task_id'],params['package_id'])
        assert old.checksum==params['package_checksum']
        assert revisions.execute(s,rev['id'],Provider,None)==result


def test_invalid_change_does_not_create_attempt_or_package(client,generated,task_repository):
    class Provider:
        def __init__(self,c):pass
        def complete(self,m):return {'content':json.dumps({'changes':{'test_app.py':'bad'}}),
            'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    with task_repository._session_factory() as s:
        rev=revisions.create(s,output_profile=REPAIR_PROFILE,**(generated[0]|{'auto_test':False}));s.commit()
        result=revisions.execute(s,rev['id'],Provider,None)
        assert result['state']=='failed' and result['new_package_id'] is None
        run=s.get(LocalInference,result['inference_id'])
        assert run.attempt_id is None and run.error_code=='invalid_file_repair'
        assert json.loads(s.get(Artifact,run.metrics['raw_artifact_id']).content)=={'changes':{'test_app.py':'bad'}}


def test_changed_context_discards_patch(client,generated,task_repository):
    from app.models.delegation import TaskDelegation
    class Provider:
        def __init__(self,c):pass
        def complete(self,m):
            with task_repository._session_factory() as other:
                other.get(TaskDelegation,generated[0]['task_id']).execution_brief='Scope changed during generation'
                other.commit()
            return {'content':json.dumps({'changes':{'README.md':'corrected'}}),
                    'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    with task_repository._session_factory() as s:
        rev=revisions.create(s,output_profile=REPAIR_PROFILE,**(generated[0]|{'auto_test':False}));s.commit()
        result=revisions.execute(s,rev['id'],Provider,None)
        assert result['state']=='stale' and result['new_package_id'] is None
        assert s.get(LocalInference,result['inference_id']).attempt_id is None
