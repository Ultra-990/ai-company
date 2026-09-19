"""Read-only navigation through existing stages; never grants execution or release."""
from hashlib import sha256


def accepted_result(task: dict, attempt) -> bool:
    return bool(
        task['status'] == 'completed' and attempt
        and attempt.status == 'completed'
        and attempt.verification_status == 'accepted' and attempt.verified_at
        and attempt.result_content
        and attempt.result_checksum == sha256(attempt.result_content.encode()).hexdigest()
    )


def project_guidance(task_ids, tasks, attempts, runs, project_status):
    """Use persisted order, latest attempt and *all* unsettled inference records.

    ``runs`` contains only id/task_id/state, not prompts or model output.
    Actions name local navigation targets, never URLs or execution commands.
    """
    by_id = {task['id']: task for task in tasks}
    stages = []
    for task_id in task_ids:
        task = by_id.get(task_id)
        attempt = attempts.get(task_id)
        related = [run for run in runs if run.task_id == task_id]
        unsettled = [run for run in related if run.state in {'queued', 'running', 'uncertain'}]
        action = 'task'
        if not task:
            state, reason = 'inconsistent', 'Brakuje zadania w tym projekcie. Sprawdź powiązania danych.'
            action = 'details'
        elif unsettled:
            state, reason = 'execution_hold', 'Istnieje oczekujące, trwające lub niepewne wykonanie. Sprawdź historię przed ponowieniem.'
            action = 'history'
        elif accepted_result(task, attempt):
            state, reason = 'accepted', 'Odebrano wynik ostatniej próby; treść i suma kontrolna są zgodne.'
        elif task['status'] == 'cancelled':
            state, reason = 'cancelled', 'Etap anulowany. Wymagana decyzja o zakresie projektu.'
        elif (attempt and attempt.status == 'awaiting_review'
              and task['status'] == 'in_progress'):
            state, reason = 'review', 'Wynik czeka na ocenę. Akceptacja i odrzucenie wymagają osobnej decyzji.'
        elif task['status'] == 'completed':
            state, reason = 'unverified', 'Status ukończony nie ma spójnego odbioru ostatniej próby. Sprawdź dowody.'
        elif attempt and attempt.verification_status == 'rejected':
            state, reason = 'repair', 'Wynik odrzucono. Sprawdź uwagi odbioru i blokady przed przygotowaniem poprawy.'
        elif related:
            state, reason = 'inspect', 'Sprawdź ostatnie wykonanie i jego wynik przed przygotowaniem kolejnej instrukcji.'
            action = 'history'
        elif not task.get('delegation'):
            state, reason = 'assignment', 'Przygotuj zespół działu i przydziel kierownika, wykonawcę oraz kontrolera.'
            action = 'assignment'
        elif task['delegation'].get('planning_blockers'):
            state = 'blocked'
            reason = ' · '.join(task['delegation']['planning_blockers'])
        elif task['status'] == 'pending' and attempt is None:
            state, reason = 'instruction', 'Otwórz etap i przygotuj instrukcję. Jej zapis nie uruchamia modelu.'
        else:
            state, reason = 'inspect', 'Sprawdź stan zadania i ostatni wynik. Nie uruchamiaj ponownie pracy w ciemno.'
        stages.append({'task_id': task_id, 'title': task['title'] if task else 'Brak zadania',
                       'state': state, 'reason': reason, 'action': action})

    current = next((stage for stage in stages if stage['state'] == 'execution_hold'), None)
    if current is None:
        current = next((stage for stage in stages if stage['state'] != 'accepted'), None)
    if project_status == 'cancelled':
        current = {'task_id': None, 'title': 'Projekt anulowany', 'state': 'cancelled',
                   'reason': 'Najpierw wyjaśnij zakres i decyzję właściciela. Nie kontynuuj wykonania.', 'action': 'details'}
    elif len(set(task_ids)) != len(task_ids):
        current = {'task_id': None, 'title': 'Powtórzone zadanie w planie', 'state': 'inconsistent',
                   'reason': 'Jedno zadanie przypisano do kilku etapów. Sprawdź strukturę planu.', 'action': 'details'}
    elif not stages:
        current = {'task_id': None, 'title': 'Brak etapów', 'state': 'inconsistent',
                   'reason': 'Projekt nie ma przypisanych etapów realizacji.', 'action': 'details'}
    elif current is None:
        current = {'task_id': None, 'title': 'Sprawdź pliki, testy i wydanie', 'state': 'stages_accepted',
                   'reason': 'Odebrano etapy. To nie potwierdza gotowości paczki, publikacji ani odbioru klienta.',
                   'action': 'artifacts'}
    return {'version': 1, 'stages': stages, 'current': current,
            'accepted_stages': sum(stage['state'] == 'accepted' for stage in stages),
            'total_stages': len(stages), 'execution_authorized': False, 'release_authorized': False}
