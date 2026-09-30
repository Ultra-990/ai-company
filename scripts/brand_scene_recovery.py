"""Development completion after an exhausted second-logo stage; never resets an exam."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import time
from scripts import brand_school as b, brand_artwork_repair as art, brand_scene_contract as scoped
from scripts import verify_brand_package as evidence
from scripts.brand_full_exam import exercise_context

CONTRACT = 'brand-second-logo-recovery.v1'
SELECTION_SCHEMA = {'type':'object','additionalProperties':False,'required':['selected','reason'],
    'properties':{'selected':{'enum':['a','b']},'reason':{'type':'string','minLength':20,'maxLength':400}}}


def source_values(source):
    value = evidence.read(source/'report.json')
    if (value.get('schema') != 'restaurant-brand-school.v1' or value.get('status') != 'failed'
            or value.get('stages') != ['plan','logo-a'] or 'repair_contract' in value or 'scene_recovery_contract' in value
            or value['brief_sha256'] != sha256(json.dumps(value['brief'],sort_keys=True).encode()).hexdigest()):
        raise ValueError('Original exhausted second-logo source required')
    for name,digest in value['artifacts'].items():
        path=evidence.bounded(source/name)
        if not path.resolve().is_relative_to(source.resolve()) or b.school.checksum(path)!=digest:
            raise ValueError('Original source changed')
    raw={stage:evidence.chain(source,stage,value)[0] for stage in ('plan','logo-a')}
    try: evidence.chain(source,'logo-b',value)
    except ValueError as error:
        if str(error)!='All brand attempts rejected': raise
    else: raise ValueError('Exhausted original second-logo budget required')
    raw['logo-b']=evidence.read(source/'logo-b-revision-2-response.json')['content']
    with exercise_context(value['brief']):
        plan=b.plan_value(raw['plan']); logo=b.compile_scene(raw['logo-a'],plan,kind='logo')
    if plan!=evidence.read(source/'plan.json'): raise ValueError('Protected plan changed')
    return value,raw,plan,logo


def payloads(brief,plan,raw,logos=None,chosen=None):
    return {
        'logo-b': {'brief':brief,'plan':plan,'previous_scene':json.loads(raw['logo-b']),
            'required_texts':scoped.expected_copy('logo',plan,brief),'direction':plan['concept_b'],
            'task':'Complete your previously rejected second logo. Preserve the required restaurant name; choose and return the entire corrected scene yourself.'},
        'selection': {'brief':brief,'plan':plan,'logo_sources':logos,
            'task':'Select one concept and explain in one short complete sentence. Selection from scene data is not independent visual approval.'},
        'card': {'brief':brief,'plan':plan,'chosen_logo_svg':chosen,
            'required_texts':scoped.expected_copy('card',plan,brief),
            'task':'Design the business card using the selected logo and exactly the approved four text lines.'}}


def run(source):
    source=Path(source); original,raw,plan,first=source_values(source)
    resources=b.school.check_idle()
    config=b.configuration()|{'sampling_profile':'qwen-deliberate-trial.v1','think':True,
        'num_ctx':16384,'num_predict':8192,'num_thread':4,'timeout_seconds':180}
    if (config['model'],config['digest'])!=(original['model'],original['digest']): raise ValueError('Pinned original author required')
    out=Path(tempfile.mkdtemp(prefix='scene-recovery-',dir=b.ROOT)); code=out/'implementation';code.mkdir()
    for name in ('brand_scene_recovery.py','brand_scene_contract.py','brand_artwork_repair.py','brand_school.py',
                 'verify_brand_package.py','brand_full_exam.py','brand_spatial_review.py','render_school_svg.py','vector_school_contract.py','vector_structured_source.py'):
        shutil.copyfile(Path(__file__).parent/name,code/name)
    shutil.copyfile(Path(__file__).parents[1]/'app/services/local_ollama.py',code/'local_ollama.py')
    report={key:original[key] for key in ('schema','brief','brief_sha256','model','digest')}
    report.update(status='running',config=config,resources_before=resources,stages=['plan','logo-a'],checks={},
        scene_recovery_contract=CONTRACT,source=str(source),source_report_sha256=b.school.checksum(source/'report.json'),
        max_additional_model_calls=9,fresh_exam=False,training_exported=False,training_started=False,
        production_changed=False,autonomy_qualified=False,exam_score_changed=False,print_ready=False,commercial_delivery_approved=False)
    started=time.monotonic(); print(json.dumps({'output':str(out)}),flush=True)
    def check(stage,kind,chosen=None):
        attempt=0
        def validate(answer):
            nonlocal attempt
            svg=scoped.compile_scene(answer,plan,kind=kind,brief=original['brief'],logo=chosen)
            folder=out/(stage+'-layout-'+str(attempt));attempt+=1
            findings=art.diagnose(svg,folder,plan,kind,strict_card=True,full_scene=True)
            if findings['issues']:raise ValueError(json.dumps(findings))
            return svg
        return validate
    try:
        with exercise_context(original['brief']):
            for stage in ('plan','logo-a'):
                for path in source.glob(stage+'*-*.json'):
                    if any(path.name.endswith('-'+suffix+'.json') for suffix in ('request','response','feedback')):
                        shutil.copyfile(path,out/path.name)
            b.school.save(out/'plan.json',plan);(out/'logo-a.svg').write_text(first)
            initial=art.diagnose(first,out/'protected-logo',plan,'logo',full_scene=True)
            b.school.save(out/'protected-logo-feedback.json',initial)
            if initial['issues']:raise ValueError('Protected first logo needs its own repair before completion')
            request=payloads(original['brief'],plan,raw)['logo-b']
            second=b.validated_call(out,'logo-b',b.INSTRUCTION+'\n'+scoped.rules('logo'),json.dumps(request),
                scoped.schema('logo',plan,original['brief']),config,check('logo-b','logo'))
            logos={'a':first,'b':second};(out/'logo-b.svg').write_text(second);report['stages'].append('logo-b')
            if first==second:raise ValueError('Two distinct logo concepts required')
            request=payloads(original['brief'],plan,raw,logos=logos)['selection']
            selection=b.validated_call(out,'selection',b.INSTRUCTION,json.dumps(request),SELECTION_SCHEMA,config,b.selected_value)
            report['selection']=selection;chosen=logos[selection['selected']]
            request=payloads(original['brief'],plan,raw,chosen=chosen)['card']
            card=b.validated_call(out,'card',b.INSTRUCTION+'\n'+scoped.rules('card'),json.dumps(request),
                scoped.schema('card',plan,original['brief']),config,check('card','card',chosen))
            report['stages'].append('card');b.assemble(out,plan,logos,selection,card,report)
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error)[:600])
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        report['artifacts']={str(p.relative_to(out)):b.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name!='report.json'}
        b.school.save(out/'report.json',report)
    print(json.dumps({'output':str(out),'status':report['status'],'elapsed_seconds':report['elapsed_seconds']}),flush=True)
    return out,report


def verify_proof(svg,folder,plan,kind):
    if evidence.bounded(folder/'artwork.svg').read_text()!=svg:raise ValueError('Accepted scene proof changed')
    measured=evidence.read(folder/'render.json')
    issues=b.quality_issues(measured,'brand_'+kind)+scoped.margin_findings(svg,measured,kind,plan['paper'])
    if kind=='card':issues+=art.card_decoration_findings(svg,measured,plan['paper'])
    else:
        mono=evidence.read(folder/'monochrome/render.json')
        if evidence.bounded(folder/'monochrome/artwork.svg').read_text()!=b.monochrome(svg,plan['monochrome_ink']):
            raise ValueError('Monochrome conversion changed')
        art.verify_contributions(folder,measured);art.verify_contributions(folder/'monochrome',mono)
        issues+=art.monochrome_findings(measured,mono)
    if issues:raise ValueError('Accepted scene still has measured defects')


def verify_origin(out,report):
    source=Path(report['source']);original,raw,plan,first=source_values(source)
    if (report['scene_recovery_contract']!=CONTRACT or report['max_additional_model_calls']!=9
            or b.school.checksum(source/'report.json')!=report['source_report_sha256']
            or any(report[k]!=original[k] for k in ('brief','brief_sha256','model','digest'))
            or any(report.get(k) is not False for k in ('fresh_exam','exam_score_changed','training_exported','autonomy_qualified'))):
        raise ValueError('Recovery origin or nonqualification boundary changed')
    for stage in ('plan','logo-a'):
        for p in out.glob(stage+'*-*.json'):
            if p.read_bytes()!=evidence.bounded(source/p.name).read_bytes():raise ValueError('Protected original stage changed')
    verify_proof(first,out/'protected-logo',plan,'logo')
    with exercise_context(original['brief']):
        second_raw,_=evidence.chain(out,'logo-b',report)
        second=scoped.compile_scene(second_raw,plan,kind='logo',brief=original['brief'])
        logos={'a':first,'b':second}
        selected_raw,_=evidence.chain(out,'selection',report);selected=b.selected_value(selected_raw)
        if selected!=report['selection']:raise ValueError('Recovery selection changed')
        chosen=logos[selected['selected']]
        card_raw,_=evidence.chain(out,'card',report)
        card=scoped.compile_scene(card_raw,plan,kind='card',brief=original['brief'],logo=chosen)
        expected=payloads(original['brief'],plan,raw,logos,chosen)
        for stage in ('logo-b','selection','card'):
            kind='card' if stage=='card' else 'logo'
            system=b.INSTRUCTION+('' if stage=='selection' else '\n'+scoped.rules(kind))
            schema=SELECTION_SCHEMA if stage=='selection' else scoped.schema(kind,plan,original['brief'])
            if evidence.read(out/(stage+'-request.json'))!={'system':system,'user':json.dumps(expected[stage]),'format':schema}:
                raise ValueError('Recovery contains changed instructions or manual hints')
        for stage,svg,kind in [('logo-b',second,'logo'),('card',card,'card')]:
            proofs=[p for p in out.glob(stage+'-layout-*') if (p/'artwork.svg').is_file() and evidence.bounded(p/'artwork.svg').read_text()==svg]
            if len(proofs)!=1:raise ValueError('Exact accepted recovery proof required')
            verify_proof(svg,proofs[0],plan,kind)
        for name,svg,kind in [('logo-a',first,'logo'),('logo-b',second,'logo'),('business-card',card,'card')]:
            measured=evidence.read(out/name/'render.json')
            if scoped.margin_findings(svg,measured,kind,plan['paper']):
                raise ValueError('Final recovery export violates margins')
            if kind=='card' and art.card_decoration_findings(svg,measured,plan['paper']):
                raise ValueError('Final recovery card decoration overlaps text')
    calls=sum(evidence.chain(out,stage,report)[1]['requests'] for stage in ('logo-b','selection','card'))
    if calls>9:raise ValueError('Additional development budget exceeded')
    return {'schema':CONTRACT,'additional_model_calls':calls,'protected_stages':['plan','logo-a'],
            'fresh_exam':False,'original_failed_attempts_preserved':True}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True)
    _,report=run(parser.parse_args().run)
    raise SystemExit(int(report['status']!='pending_independent_visual_review'))
