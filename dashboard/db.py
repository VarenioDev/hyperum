"""
Подключение к PostgreSQL и кэшированные запросы для дашборда.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd
import streamlit as st

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
TENANT = os.getenv("HYPERUM_TENANT_DEFAULT", "school_lyceum")


@st.cache_resource
def get_engine():
    return create_engine(DB_URL, pool_pre_ping=True)


@st.cache_data(ttl=120)
def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


# ─── Справочники ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_classes() -> list[str]:
    df = query("""
        SELECT DISTINCT name FROM groups
        WHERE kind = 'class' AND name IN ('10А','10Б','10Г')
        ORDER BY name
    """)
    return df["name"].tolist()


@st.cache_data(ttl=300)
def get_skills() -> pd.DataFrame:
    return query("""
        SELECT id, name, module, topic FROM skills
        ORDER BY module, topic, name
    """)


# ─── Основные запросы ────────────────────────────────────────

@st.cache_data(ttl=120)
def class_overview() -> pd.DataFrame:
    return query("""
        SELECT g.name AS class,
               COUNT(DISTINCT u.id) AS students,
               ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
               COUNT(*) FILTER (WHERE sm.mastery >= 0.8) AS strong_skills,
               COUNT(*) FILTER (WHERE sm.mastery < 0.5) AS weak_skills
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN memberships m ON m.user_id = u.id
        JOIN groups g ON g.id = m.group_id
        WHERE g.name IN ('10А','10Б','10Г')
        GROUP BY g.name
        ORDER BY g.name
    """)


@st.cache_data(ttl=120)
def skill_class_pivot() -> pd.DataFrame:
    return query("""
        SELECT s.name AS skill,
               ROUND(AVG(CASE WHEN g.name = '10А' THEN sm.mastery END)::numeric, 2) AS class_10a,
               ROUND(AVG(CASE WHEN g.name = '10Б' THEN sm.mastery END)::numeric, 2) AS class_10b,
               ROUND(AVG(CASE WHEN g.name = '10Г' THEN sm.mastery END)::numeric, 2) AS class_10g
        FROM skills s
        LEFT JOIN student_mastery sm ON sm.skill_id = s.id
        LEFT JOIN users u ON u.id = sm.student_id
        LEFT JOIN memberships m ON m.user_id = u.id
        LEFT JOIN groups g ON g.id = m.group_id
        GROUP BY s.name
        ORDER BY s.name
    """)


@st.cache_data(ttl=120)
def problems_by_class() -> pd.DataFrame:
    return query("""
        SELECT g.name AS class,
               s.name AS skill,
               ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
               COUNT(*) AS students,
               COUNT(*) FILTER (WHERE sm.mastery < 0.5) AS weak_count
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN memberships m ON m.user_id = u.id
        JOIN groups g ON g.id = m.group_id
        JOIN skills s ON s.id = sm.skill_id
        WHERE g.name IN ('10А','10Б','10Г')
        GROUP BY g.name, s.name
        ORDER BY g.name, avg_mastery ASC
    """)


@st.cache_data(ttl=120)
def weak_students() -> pd.DataFrame:
    return query("""
        SELECT g.name AS class,
               u.full_name,
               ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
               COUNT(*) FILTER (WHERE sm.mastery < 0.5) AS weak_skills
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN memberships m ON m.user_id = u.id
        JOIN groups g ON g.id = m.group_id
        WHERE g.name IN ('10А','10Б','10Г')
        GROUP BY g.name, u.full_name
        HAVING AVG(sm.mastery) < 0.7
        ORDER BY g.name, avg_mastery ASC
    """)


@st.cache_data(ttl=120)
def students_mastery_matrix(class_filter: str | None = None) -> pd.DataFrame:
    params = {}
    where = "g.name IN ('10А','10Б','10Г')"
    if class_filter and class_filter != "Все":
        where += " AND g.name = :c"
        params["c"] = class_filter

    return query(f"""
        SELECT u.full_name AS student, g.name AS class,
               s.name AS skill, sm.mastery
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN memberships m ON m.user_id = u.id
        JOIN groups g ON g.id = m.group_id
        JOIN skills s ON s.id = sm.skill_id
        WHERE {where}
        ORDER BY g.name, u.full_name, s.name
    """, params)


@st.cache_data(ttl=120)
def all_students(class_filter: str | None = None) -> pd.DataFrame:
    params = {}
    where = "g.name IN ('10А','10Б','10Г')"
    if class_filter and class_filter != "Все":
        where += " AND g.name = :c"
        params["c"] = class_filter

    return query(f"""
        SELECT g.name AS class,
               u.full_name,
               ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
               COUNT(*) AS skills_total,
               COUNT(*) FILTER (WHERE sm.mastery >= 0.8) AS strong_skills,
               COUNT(*) FILTER (WHERE sm.mastery < 0.5) AS weak_skills
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN memberships m ON m.user_id = u.id
        JOIN groups g ON g.id = m.group_id
        WHERE {where}
        GROUP BY g.name, u.full_name
        ORDER BY g.name, u.full_name
    """, params)


@st.cache_data(ttl=60)
def student_detail(full_name: str) -> pd.DataFrame:
    return query("""
        SELECT s.name AS skill,
               ROUND(sm.mastery::numeric, 2) AS mastery,
               sm.attempts,
               sm.correct,
               sm.updated_at::date AS last_update
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN skills s ON s.id = sm.skill_id
        WHERE u.full_name = :n
        ORDER BY sm.mastery ASC
    """, {"n": full_name})


@st.cache_data(ttl=60)
def student_responses(full_name: str) -> pd.DataFrame:
    return query("""
        SELECT t.code, s.name AS skill,
               r.answer, r.correct, r.created_at::timestamp(0) AS answered_at
        FROM responses r
        JOIN users u ON u.id = r.student_id
        JOIN tasks t ON t.id = r.task_id
        LEFT JOIN task_labels tl ON tl.task_id = t.id
        LEFT JOIN skills s ON s.id = tl.skill_id
        WHERE u.full_name = :n
        ORDER BY r.created_at DESC
    """, {"n": full_name})


@st.cache_data(ttl=120)
def task_stats() -> pd.DataFrame:
    return query("""
        SELECT t.code,
               LEFT(t.text, 70) AS text_preview,
               s.name AS skill,
               COUNT(*) AS attempts,
               COUNT(*) FILTER (WHERE r.correct) AS correct,
               ROUND(AVG(CASE WHEN r.correct THEN 1.0 ELSE 0 END)::numeric, 2) AS success_rate
        FROM responses r
        JOIN tasks t ON t.id = r.task_id
        LEFT JOIN task_labels tl ON tl.task_id = t.id
        LEFT JOIN skills s ON s.id = tl.skill_id
        GROUP BY t.code, t.text, s.name
        ORDER BY success_rate ASC
    """)


@st.cache_data(ttl=120)
def mastery_distribution(class_filter: str | None = None) -> pd.DataFrame:
    params = {}
    where = "g.name IN ('10А','10Б','10Г')"
    if class_filter and class_filter != "Все":
        where += " AND g.name = :c"
        params["c"] = class_filter

    return query(f"""
        SELECT CASE
                 WHEN sm.mastery >= 0.9 THEN '0.9-1.0'
                 WHEN sm.mastery >= 0.7 THEN '0.7-0.9'
                 WHEN sm.mastery >= 0.5 THEN '0.5-0.7'
                 WHEN sm.mastery >= 0.3 THEN '0.3-0.5'
                 ELSE '0.0-0.3'
               END AS bucket,
               COUNT(*) AS count
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN memberships m ON m.user_id = u.id
        JOIN groups g ON g.id = m.group_id
        WHERE {where}
        GROUP BY bucket
        ORDER BY bucket DESC
    """, params)