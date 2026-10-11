import json
import pytest

from scripts import check_business_website,check_service_quote_transfer,check_workshop_catalog
from scripts import workshop_catalog_case
from tests import test_business_website_delivery as delivery


def clear(monkeypatch):
    for name in ('AIC_BUSINESS_WEBSITE_PILOT','AIC_SERVICE_QUOTE_TRANSFER_PILOT',
                 'AIC_WORKSHOP_CATALOG_PILOT'):
        monkeypatch.delenv(name,raising=False)


def test_shared_delivery_selects_workshop_and_three_flags_are_exclusive(monkeypatch):
    clear(monkeypatch);monkeypatch.setenv('AIC_WORKSHOP_CATALOG_PILOT','1')
    selected=delivery.selected_delivery_case()
    assert selected['module'] is workshop_catalog_case
    assert selected['output_env']=='AIC_WORKSHOP_CATALOG_OUTPUT'
    assert selected['schema']=='workshop-catalog-delivery.v1'
    assert selected['archive']=='workshop-catalog-candidate.zip'
    for other in ('AIC_BUSINESS_WEBSITE_PILOT','AIC_SERVICE_QUOTE_TRANSFER_PILOT'):
        monkeypatch.setenv(other,'1')
        with pytest.raises(ValueError,match='exactly one'):delivery.selected_delivery_case()
        monkeypatch.setenv(other,'0')


def test_workshop_wrapper_dry_run_never_invokes_subprocess(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['check_workshop_catalog.py'])
    monkeypatch.setattr(check_workshop_catalog.subprocess,'run',
                        lambda *args,**kwargs:pytest.fail('unexpected model/Docker subprocess'))
    assert check_workshop_catalog.main()==0
    assert json.loads(capsys.readouterr().out)=={'model_invoked':False,'docker_invoked':False,
        'scenario':'workshop-catalog','required_flag':'--run'}


@pytest.mark.parametrize('wrapper,module_name',[('business',check_business_website),
                                                ('service',check_service_quote_transfer)])
def test_existing_wrappers_explicitly_disable_workshop_env(monkeypatch,tmp_path,wrapper,module_name):
    monkeypatch.setattr('sys.argv',[f'check_{wrapper}.py','--run'])
    monkeypatch.setattr(module_name.tempfile,'mkdtemp',lambda **kwargs:str(tmp_path/'pilot'))
    (tmp_path/'pilot').mkdir()
    captured={}
    def run(*args,**kwargs):
        captured.update(kwargs['env']);return type('Result',(),{'returncode':0})()
    monkeypatch.setattr(module_name.subprocess,'run',run)
    assert module_name.main()==0
    assert captured['AIC_WORKSHOP_CATALOG_PILOT']=='0'
