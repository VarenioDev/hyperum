"""Teacher-controlled generation and replacement, without persisting previews."""
from collections import deque
from sqlalchemy import text
from backend.services import assignments_service as base


class GenerationError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def get_owned_group(session, group_id, teacher_id):
    row = session.execute(text("""
        SELECT name, tenant_id FROM groups WHERE id=:gid AND owner_id=:teacher
    """), {"gid": group_id, "teacher": teacher_id}).fetchone()
    if not row:
        raise GenerationError("Класс не найден или недоступен", 404)
    return row


def selected_students(session, group_id, student_ids):
    students = base.get_group_students(session, group_id)
    if student_ids is not None:
        wanted = set(student_ids)
        if not wanted or len(wanted) != len(student_ids):
            raise GenerationError("Выбери учеников без повторений")
        if not wanted.issubset({s['id'] for s in students}):
            raise GenerationError("Выбраны ученики вне класса или без подтверждённого доступа")
        students = [s for s in students if s['id'] in wanted]
    if not students:
        raise GenerationError("В классе нет доступных учеников")
    return students


def average_mastery(profiles, skills):
    # Include every selected student; no attempts means neutral mastery 0.5.
    return {skill: sum(p.get(skill, 0.5) for p in profiles) / len(profiles) for skill in skills}


def usage_stats(students):
    counts = {}
    for student in students:
        for task in student['tasks']:
            counts[task['task_id']] = counts.get(task['task_id'], 0) + 1
    return dict(total_tasks_used=sum(counts.values()), unique_tasks_used=len(counts),
                max_usage=max(counts.values(), default=0))


def generate_for_group(session, group_id, topic, n_tasks, model='deepseek', *,
                       teacher_id, student_ids=None, personalize=True):
    group = get_owned_group(session, group_id, teacher_id)
    students = selected_students(session, group_id, student_ids)
    skills = base.get_topic_skills(session, topic)
    if not skills:
        raise GenerationError(f"По теме «{topic}» нет навыков")
    candidates = base.get_candidate_tasks(session, skills, model=model, author_id=teacher_id)
    if len(candidates) < n_tasks:
        raise GenerationError(f"По теме доступно {len(candidates)} заданий. Уменьши число заданий в тесте")
    profiles = {s['id']: base.get_student_mastery(session, s['id']) for s in students}
    result = []
    if not personalize:
        all_skills = sorted({skill for c in candidates for skill in c['all_skills']})
        mastery = average_mastery(list(profiles.values()), all_skills)
        tasks = base.select_tasks_for_student(mastery, candidates, n=n_tasks)
        result = [dict(student_id=s['id'], full_name=s['full_name'],
                       tasks=[dict(t) for t in tasks], blocked_skills=[]) for s in students]
    else:
        counts = {}
        shuffled = list(students)
        base.random.shuffle(shuffled)
        for student in shuffled:
            blocked = base.get_weak_prerequisites(student['id'], skills)
            available = [c for c in candidates if c['primary_skill'] not in blocked]
            if not available:
                available = candidates  # Preserve the existing cold-start fallback.
            if len(available) < n_tasks:
                raise GenerationError(f"Для ученика {student['full_name']} доступно {len(available)} заданий с учётом освоения навыков. Уменьши число заданий")
            tasks = base.select_tasks_for_student(profiles[student['id']], available,
                                                  n=n_tasks, usage_counter=counts)
            for task in tasks:
                counts[task['task_id']] = counts.get(task['task_id'], 0) + 1
            result.append(dict(student_id=student['id'], full_name=student['full_name'],
                               tasks=tasks, blocked_skills=sorted(blocked)))
    result.sort(key=lambda s: s['full_name'])
    return dict(class_name=group[0], topic=topic, n_tasks=n_tasks, personalize=personalize,
                students=result, usage_stats=usage_stats(result))


def skill_distances(skill_id, topic_skills):
    """Undirected prerequisite distance; paths never leave the selected topic."""
    edges = {}
    try:
        with base.neo4j_session() as graph:
            rows = graph.run("""
                MATCH (a:Skill)-[:PREREQUISITE]->(b:Skill)
                WHERE a.id IN $skills AND b.id IN $skills
                RETURN DISTINCT a.id AS source, b.id AS target
            """, skills=topic_skills)
            for row in rows:
                edges.setdefault(row['source'], set()).add(row['target'])
                edges.setdefault(row['target'], set()).add(row['source'])
    except Exception:
        return {skill_id: 0}
    distances = {skill_id: 0}
    queue = deque([skill_id])
    while queue:
        current = queue.popleft()
        for neighbor in edges.get(current, set()):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return distances


def regenerate_task(session, group_id, teacher_id, topic, student_ids, personalize,
                    task_id, exclude_task_ids):
    get_owned_group(session, group_id, teacher_id)
    students = selected_students(session, group_id, student_ids)
    if personalize and len(students) != 1:
        raise GenerationError("Для персональной замены выбери одного ученика")
    skills = base.get_topic_skills(session, topic)
    candidates = base.get_candidate_tasks(session, skills, author_id=teacher_id)
    current = next((t for t in candidates if t['task_id'] == task_id), None)
    if current is None:
        raise GenerationError("Исходное задание недоступно в выбранной теме", 404)
    profiles = [base.get_student_mastery(session, s['id']) for s in students]
    mastery = average_mastery(profiles, sorted({skill for c in candidates for skill in c['all_skills']}))
    blocked = base.get_weak_prerequisites(students[0]['id'], skills) if personalize else set()
    excluded = set(exclude_task_ids) | {task_id}
    available = [c for c in candidates if c['task_id'] not in excluded and c['primary_skill'] not in blocked]
    same_skill = [c for c in available if c['primary_skill'] == current['primary_skill']]
    distances = {current['primary_skill']: 0} if same_skill else skill_distances(current['primary_skill'], skills)
    available = same_skill or [c for c in available if c['primary_skill'] in distances]
    if not available:
        raise GenerationError("В этой теме больше нет подходящих заданий для замены", 404)
    scored = base.select_tasks_for_student(mastery, available, n=len(available))
    replacement = min(scored, key=lambda t: (distances[t['primary_skill']],
                      abs(t['difficulty'] - current['difficulty']), -t['score']))
    return dict(task=replacement, match='same_skill' if replacement['primary_skill'] == current['primary_skill'] else 'neighboring_skill')


def validate_saved_test(session, generated, group_id, teacher_id):
    group = get_owned_group(session, group_id, teacher_id)
    selected_students(session, group_id, [s['student_id'] for s in generated['students']])
    candidates = base.get_candidate_tasks(session, base.get_topic_skills(session, generated['topic']), author_id=teacher_id)
    allowed = {t['task_id'] for t in candidates}
    lists = [[t['task_id'] for t in s['tasks']] for s in generated['students']]
    for ids in lists:
        if not ids or len(ids) > 20 or len(set(ids)) != len(ids) or not set(ids).issubset(allowed):
            raise GenerationError("В тесте есть повторяющиеся, недоступные или неподходящие теме задания")
    if len({len(ids) for ids in lists}) != 1:
        raise GenerationError("Число заданий должно совпадать для всех получателей")
    if not generated.get('personalize', True) and any(ids != lists[0] for ids in lists):
        raise GenerationError("В общем тесте набор и порядок заданий должны совпадать для всех")
    return group
