"""Owner-defined, immutable HTTP examples. No execution in plan creation/evaluation."""
import json
import math
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.services.application_preview import validate_path
from app.services.package_checks import check_json_depth
from app.services.requirement_checks import context, digest
from app.services.workspace_packages import canonical_json

NAME = 'organization-os.acceptance-plan.v1'
EXECUTION_CONFIG = Path(__file__).resolve().parents[2] / 'config/acceptance_execution.json'


def execution_enabled():
    try:
        return json.loads(EXECUTION_CONFIG.read_text()).get('enabled') is True
    except (OSError, ValueError, AttributeError):
        return False


class Case(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    criterion_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    title: str = Field(min_length=3, max_length=120)
    path: str = Field(max_length=850)
    status: int = Field(ge=200, le=499)
    json_field: str | None = Field(default=None, pattern=r'^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){0,3}$', max_length=120)
    expected: str | int | float | bool | None = None

    @field_validator('path')
    @classmethod
    def local_get(cls, value):
        return validate_path(value)

    @field_validator('title')
    @classmethod
    def text(cls, value):
        if not value.strip() or '\x00' in value:
            raise ValueError('Nieprawidłowa nazwa przypadku.')
        return value

    @model_validator(mode='after')
    def bounded_expectation(self):
        if self.json_field is None and self.expected is not None:
            raise ValueError('Wskaż pole JSON dla oczekiwanej wartości.')
        if isinstance(self.expected, str) and (len(self.expected) > 500 or '\x00' in self.expected):
            raise ValueError('Wartość tekstowa przekracza limit.')
        if type(self.expected) in {int, float} and (abs(self.expected) > 2**53 or not math.isfinite(self.expected)):
            raise ValueError('Wartość liczbowa przekracza bezpieczny zakres JSON.')
        return self


Cases = Annotated[list[Case], Field(min_length=1, max_length=4)]


def create(session, task_id, package_id, request_id, source_checksum, scope_checksum, cases):
    source, current_scope, criteria = context(session, task_id, package_id)
    if source.checksum != source_checksum or current_scope != scope_checksum:
        raise ValueError('Zmieniły się źródła lub zakres. Odśwież wymagania.')
    if not 1 <= len(cases) <= 4:
        raise ValueError('Plan zawiera 1–4 przypadki.')
    cases = [Case.model_validate(c).model_dump() for c in cases]
    if any(c['criterion_id'] not in {item['id'] for item in criteria} for c in cases):
        raise ValueError('Przypadek musi dotyczyć kryterium tego zlecenia.')
    if len({canonical_json(c) for c in cases}) != len(cases):
        raise ValueError('Nie powtarzaj identycznych przypadków.')
    payload = dict(schema=NAME, task_id=task_id, source_package_id=package_id,
                   source_checksum=source_checksum, scope_checksum=scope_checksum, cases=cases)
    content = canonical_json(payload)
    name = NAME + ':' + request_id
    old = session.scalar(select(Artifact).where(Artifact.name == name))
    if old:
        if old.content != content or digest(content) != old.checksum:
            raise ValueError('Ten identyfikator wskazuje inny plan.')
        return view(old, payload)
    row = Artifact(task_id=task_id, project_id=source.project_id, plan_id=source.plan_id,
        artifact_type=ArtifactType.SPECIFICATION, name=name, content=content, checksum=digest(content),
        created_by='owner', description='Niezmienny plan przykładów HTTP przypisanych do wymagań. Nie wynik testów.')
    session.add(row)
    session.flush()
    session.add(AuditEvent(event_type='acceptance_plan', operation='create', allowed=True,
        decision='prepared_not_executed', reason=f'owner; task={task_id}; plan={row.id}; cases={len(cases)}'))
    return view(row, payload)


def view(row, payload):
    return {'id': row.id, 'checksum': row.checksum, **payload, 'is_test_result': False,
            'execution_enabled': execution_enabled()}


def read(session, task_id, package_id, plan_id, checksum):
    source, scope, criteria = context(session, task_id, package_id)
    row = session.get(Artifact, plan_id)
    if not row or row.task_id != task_id or row.artifact_type != ArtifactType.SPECIFICATION or not row.name.startswith(NAME + ':'):
        raise LookupError('Nie znaleziono planu przypadków dla tego zadania.')
    if (row.checksum != checksum or not row.content or digest(row.content) != checksum
            or row.project_id != source.project_id or row.plan_id != source.plan_id):
        raise ValueError('Plan przypadków ma niespójne dane.')
    data = json.loads(row.content)
    if (not isinstance(data, dict) or data.get('schema') != NAME
            or data.get('task_id') != task_id or data.get('scope_checksum') != scope
            or not isinstance(data.get('cases'), list) or not 1 <= len(data['cases']) <= 4):
        raise ValueError('Zakres planu zmienił się. Nie stosujemy starych oczekiwań.')
    for item in data['cases']:
        case = Case.model_validate(item)
        if case.criterion_id not in {c['id'] for c in criteria}:
            raise ValueError('Plan wskazuje nieaktualne kryterium.')
    # A repair may use a new source package of the SAME task/scope; expectations
    # are frozen independently of generated code and never rewritten by the model.
    return data


def evaluate(case, response):
    case = Case.model_validate(case)
    result = {'criterion_id': case.criterion_id, 'title': case.title,
              'path': case.path, 'expected_status': case.status, 'json_field': case.json_field,
              'expected': case.expected, 'passed': False, 'reason': '', 'observed': None}
    if not isinstance(response, dict) or type(response.get('status')) is not int:
        return result | {'reason': 'invalid_http_response'}
    if response['status'] != case.status:
        return result | {'reason': 'status_mismatch', 'observed': response.get('status')}
    if case.json_field is None:
        return result | {'passed': True, 'reason': 'status_matches', 'observed': response['status']}
    try:
        body = response['body']
        if not isinstance(body, str) or len(body.encode()) > 12000:
            raise ValueError('body')
        check_json_depth(body)
        def unique(pairs):
            data = {}
            for key, value in pairs:
                if key in data:
                    raise ValueError('duplicate')
                data[key] = value
            return data
        def invalid(value):
            raise ValueError('nonfinite')
        value = json.loads(body, object_pairs_hook=unique, parse_constant=invalid)
        for key in case.json_field.split('.'):
            if not isinstance(value, dict) or key not in value:
                return result | {'reason': 'missing_json_field'}
            value = value[key]
        if type(value) in {int, float} and type(case.expected) in {int, float}:
            matches = math.isfinite(value) and value == case.expected
        else:
            matches = type(value) is type(case.expected) and value == case.expected
        observed = value if value is None or type(value) in {bool, int, float, str} else '[non-scalar]'
        if isinstance(observed, str):
            observed = observed[:500]
        if type(observed) in {int, float} and (not math.isfinite(observed) or abs(observed) > 2**53):
            observed = '[number outside safe range]'
        return result | {'passed': matches, 'reason': 'value_matches' if matches else 'value_mismatch', 'observed': observed}
    except (ValueError, TypeError, KeyError, OverflowError):
        return result | {'reason': 'invalid_json_response'}
