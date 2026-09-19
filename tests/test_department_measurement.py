from sqlalchemy import select

from app.models.organization import OrganizationUnit
from app.models.project import Project
from app.models.task import Task
from app.organization_os.department_foundations import FOUNDATIONS, foundation_for


def flatten(nodes):
    return {n['key']: n for root in nodes for n in walk(root)}


def walk(node):
    yield node
    for child in node['children']:
        yield from walk(child)


def test_empty_departments_have_inventory_but_no_invented_progress(client):
    tree = client.get('/api/organization-os/tree').json()
    departments = tree['nodes'][0]['children']
    assert len(departments) == len(FOUNDATIONS) == 12
    for node in departments:
        assert node['progress'] == 0
        assert node['measurement_state'] == 'unmeasured'
        assert node['subtree_task_count'] == 0
        assert node['foundation']['review_required']
        assert len(node['foundation']['completion_criteria']) == 3
        assert node['foundation']['next_step']
        assert all(a['present'] for a in node['foundation']['artifacts'])
    assert foundation_for('unknown') is None


def attach(task_repository, key):
    task = task_repository.create(title='Izolowany pomiar')
    with task_repository._session_factory() as session:
        unit = session.scalar(select(OrganizationUnit).where(OrganizationUnit.os_key == key))
        project = Project(name='Pomiar testowy', business_goal='Test agregacji', organization_unit_id=unit.id)
        session.add(project); session.flush()
        row = session.get(Task, task.id); row.project_id = project.id; row.progress = 50
        session.commit()


def test_subtree_counts_and_partial_coverage_do_not_hide_child_tasks(client, task_repository):
    attach(task_repository, 'platform.organization-os')
    nodes = flatten(client.get('/api/organization-os/tree').json()['nodes'])
    leaf, department = nodes['platform.organization-os'], nodes['platform']
    assert leaf['progress'] == 50 and leaf['measurement_state'] == 'tracked'
    assert department['progress'] == 5  # leaf has 10% of the domain, unchanged weights
    assert department['measurement_state'] == 'partial'
    assert department['task_count'] == 0 and department['subtree_task_count'] == 1
    assert department['project_count'] == 0 and department['subtree_project_count'] == 1
    assert department['unmeasured_children'] == len(department['children']) - 1


def test_direct_parent_work_is_reported_as_unallocated_not_silently_credited(client, task_repository):
    attach(task_repository, 'platform')
    department = flatten(client.get('/api/organization-os/tree').json()['nodes'])['platform']
    assert department['progress'] == 0
    assert department['measurement_state'] == 'partial'
    assert department['direct_tasks_outside_aggregation'] == 1
    assert 'rodzicu' in department['progress_note']


def test_unassigned_history_does_not_become_department_completion(client, task_repository):
    task_repository.create(title='Nieprzypisana praca historyczna')
    overview = client.get('/api/organization-os/overview').json()
    assert overview['unassigned_tasks'] == 1 and overview['tracked_tasks'] == 0
    assert overview['organization_progress'] == 0
