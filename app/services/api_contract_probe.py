"""Inspect a sanitised API fixture, never fetch URLs or execute supplied code."""
import json
import math
import re
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.services.package_checks import check_json_depth

MAX_SAMPLE_BYTES = 32 * 1024


def strict_json(source):
    check_json_depth(source)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Powtórzone klucze JSON.')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Niedozwolona liczba JSON.')
    data = json.loads(source, object_pairs_hook=unique, parse_constant=invalid)
    pending = [data]
    while pending:
        item = pending.pop()
        if type(item) in (int, float) and (not math.isfinite(item) or abs(item) > 2**53):
            raise ValueError('Liczba poza bezpiecznym zakresem JSON.')
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return data


def tokens(pointer):
    # JSON string representation of RFC 6901, not URI fragments or JSONPath.
    if (pointer and not pointer.startswith('/')) or re.search(r'~(?![01])', pointer):
        raise ValueError('Użyj JSON Pointer, np. /data/items/0/name; ~1 oznacza /, a ~0 oznacza ~.')
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in pointer):
        raise ValueError('Niedozwolone znaki wskaźnika.')
    parts = [] if pointer == '' else pointer[1:].split('/')
    if len(parts) > 16:
        raise ValueError('Wskaźnik przekracza 16 poziomów.')
    return [p.replace('~1', '/').replace('~0', '~') for p in parts]


class Binding(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(pattern=r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')
    pointer: str = Field(max_length=256)
    expected_type: Literal['string', 'number', 'integer', 'boolean', 'object', 'array', 'null']
    required: bool = True
    nonempty: bool = False

    @field_validator('pointer')
    @classmethod
    def valid_pointer(cls, value):
        tokens(value)
        return value


class Probe(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    response_text: str = Field(min_length=1, max_length=MAX_SAMPLE_BYTES)
    observed_status: int = Field(ge=100, le=599)
    expected_status: int = Field(default=200, ge=100, le=599)
    bindings: list[Binding] = Field(min_length=1, max_length=12)

    @model_validator(mode='after')
    def bounded(self):
        try:
            size = len(self.response_text.encode('utf-8'))
        except UnicodeError as exc:
            raise ValueError('Nieprawidłowy tekst UTF-8.') from exc
        if size > MAX_SAMPLE_BYTES:
            raise ValueError('Próbka przekracza 32 KiB.')
        if len({b.name for b in self.bindings}) != len(self.bindings):
            raise ValueError('Nazwy powiązań muszą być unikalne.')
        return self


def request_schema():
    """Inline the nested binding schema for a manually bounded OpenAPI body."""
    schema = Probe.model_json_schema()
    schema['properties']['bindings']['items'] = schema.pop('$defs')['Binding']
    return schema


def resolve(data, pointer):
    for part in tokens(pointer):
        if isinstance(data, dict):
            if part not in data:
                return False, None
            data = data[part]
        elif isinstance(data, list) and re.fullmatch(r'0|[1-9][0-9]*', part):
            index = int(part)
            if index >= len(data):
                return False, None
            data = data[index]
        else:
            return False, None
    return True, data


def kind(value):
    return {str: 'string', int: 'integer', float: 'number', bool: 'boolean',
            dict: 'object', list: 'array', type(None): 'null'}[type(value)]


def inspect(probe):
    probe = Probe.model_validate(probe)
    result = dict(schema='api-contract-probe.v1', fixture_checksum=sha256(probe.response_text.encode()).hexdigest(),
                  outcome='failed', checks=[], network_used=False, model_used=False,
                  application_executed=False, release_evidence=False,
                  limitation='To kontrola wklejonej próbki i zadeklarowanego statusu, nie test połączenia, UI ani gotowości zlecenia.')
    checks = result['checks']
    checks.append(dict(name='HTTP', outcome='passed' if probe.observed_status == probe.expected_status else 'failed',
                       code='status_matches' if probe.observed_status == probe.expected_status else 'status_mismatch',
                       hint='Status podany ręcznie; nie wykonano żądania HTTP.'))
    try:
        data = strict_json(probe.response_text)
    except (ValueError, TypeError, RecursionError, OverflowError):
        checks.append(dict(name='JSON', outcome='failed', code='invalid_json',
                           hint='Sprawdź składnię, powtórzone klucze, głębokość i liczby. Próbka może być stroną HTML błędu lub logowania.'))
        return result
    for b in probe.bindings:
        found, value = resolve(data, b.pointer)
        check = dict(name=b.name, pointer=b.pointer, expected_type=b.expected_type,
                     observed_type=kind(value) if found else None)
        if not found:
            check.update(outcome='failed' if b.required else 'warning', code='missing_field',
                         hint='Sprawdź opakowanie data/records, indeks tablicy i wielkość liter. Nie zmieniamy ścieżki automatycznie.')
        elif kind(value) != b.expected_type and not (b.expected_type == 'number' and type(value) is int):
            check.update(outcome='failed', code='type_mismatch',
                         hint='Typ pola nie pasuje do odbiorcy. Liczba w cudzysłowie jest tekstem; null nie oznacza braku pola.')
        elif b.nonempty and (value is None or isinstance(value, (str, list, dict)) and not value):
            check.update(outcome='failed', code='empty_value', hint='Pole istnieje, ale jest puste. Sprawdź dane i obsługę pustych stanów.')
        else:
            check.update(outcome='passed', code='binding_matches', hint='Typ i wskazane ograniczenia pasują w tej jednej próbce.')
        checks.append(check)
    outcomes = {c['outcome'] for c in checks}
    result['outcome'] = 'failed' if 'failed' in outcomes else 'warning' if 'warning' in outcomes else 'passed'
    return result
