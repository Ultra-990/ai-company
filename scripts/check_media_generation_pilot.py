"""One real Comfy image bound to a synthetic task in an isolated Linux DB."""
import argparse
from pathlib import Path
import json
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    if not parser.parse_args().run:
        print('Use --run for one real image, isolated database, no client task changes.'); return
    from app.main import app  # Registers models; lifespan is NOT run.
    from app.core.database import Base, create_database_engine, create_session_factory
    from app.models.task import Task, TaskStatus, ApprovalStatus
    from app.services import media_generation as service
    from app.services.comfyui_provider import ComfyProvider
    from scripts.start_comfyui import check_shared_mount
    if not check_shared_mount(): raise RuntimeError('Readonly model storage unavailable')
    provider = ComfyProvider(); provider.prepare()
    out = Path(tempfile.mkdtemp(prefix='integration-check-', dir='/home/marcin/ai-company-workspaces/comfyui'))
    engine = create_database_engine(f'sqlite:///{out / "pilot.db"}')
    Base.metadata.create_all(engine); factory = create_session_factory(engine)
    report = {'passed':False, 'synthetic_task':True, 'real_image_generation':True, 'published':False}
    started = time.monotonic()
    try:
        with factory() as session:
            task = Task(title='PILOT ComfyUI — grafika, dane syntetyczne', status=TaskStatus.PENDING,
                        approval_status=ApprovalStatus.APPROVED)
            session.add(task); session.commit(); task_id = task.id
            report['job'] = service.submit(session, task_id, str(uuid4()),
                'Product photograph of a cobalt blue glass sphere on an ivory pedestal, soft studio lighting, no text.',
                20260914, provider)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            with factory() as session:
                report['job'] = service.refresh(session, task_id, report['job']['id'], provider)
            if report['job']['state'] in ('succeeded', 'failed'): break
            time.sleep(2)
        if report['job']['state'] != 'succeeded': raise RuntimeError('Pilot result not confirmed; do not resubmit automatically')
        with factory() as session:
            report['result'], image = service.read_result(session, task_id, report['job']['id'])
            assert session.get(Task, task_id).status == TaskStatus.PENDING
        (out / 'image.png').write_bytes(image)
        report.update(passed=True, task_status_unchanged=True, image=str(out/'image.png'))
    finally:
        engine.dispose()
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        (out / 'report.json').write_text(json.dumps(report, default=str, ensure_ascii=False, indent=2))
        print(json.dumps({'report':str(out/'report.json'), 'passed':report['passed']}))


if __name__ == '__main__': main()
