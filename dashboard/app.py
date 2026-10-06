"""
HyperUm — дашборд учителя.
Запуск: streamlit run dashboard/app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from db import (
    get_classes, class_overview, skill_class_pivot, problems_by_class,
    weak_students, students_mastery_matrix, all_students,
    student_detail, student_responses, task_stats, mastery_distribution,
)
from generator import (
    get_topics, get_group_id, generate_for_class, save_assignment,
)

# ─── Конфигурация ────────────────────────────────────────────
st.set_page_config(
    page_title="HyperUm",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLOR_SCALE = "RdYlGn"

# ─── Сайдбар ─────────────────────────────────────────────────
st.sidebar.title("🧠 HyperUm")
st.sidebar.caption("Система гиперперсонализации")

page = st.sidebar.radio("Раздел", [
    "📊 Обзор",
    "🔥 Тепловая карта",
    "⚠️ Проблемные темы",
    "👤 Ученики",
    "📝 Задания",
    "🎯 Создать тест",
])

classes = ["Все"] + get_classes()
selected_class = st.sidebar.selectbox("Класс", classes)

st.sidebar.divider()
if st.sidebar.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(
    "Апробация: лицей при ТПУ\n\n"
    "3 класса · 15 навыков · 53 задания"
)


# ─── Вспомогательные ─────────────────────────────────────────

def metric_row(students, avg, strong, weak):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Учеников", students)
    c2.metric("Средний mastery", f"{avg:.2f}")
    c3.metric("Сильных навыков", strong, help="mastery ≥ 0.8")
    c4.metric("Слабых навыков", weak, help="mastery < 0.5")


def download_button(df: pd.DataFrame, label: str, filename: str):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
    )


# ─── Страница: Обзор ─────────────────────────────────────────

def render_overview():
    st.title("📊 Обзор")

    df = class_overview()
    if df.empty:
        st.warning("Нет данных.")
        return

    total_students = int(df["students"].sum())
    total_strong = int(df["strong_skills"].sum())
    total_weak = int(df["weak_skills"].sum())
    total_avg = (df["avg_mastery"] * df["students"]).sum() / total_students

    metric_row(total_students, total_avg, total_strong, total_weak)

    st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Средний mastery по классам")
        fig = px.bar(
            df, x="class", y="avg_mastery",
            color="avg_mastery",
            color_continuous_scale=COLOR_SCALE,
            range_color=[0, 1],
            text="avg_mastery",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            yaxis_range=[0, 1.1],
            showlegend=False,
            coloraxis_showscale=False,
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Распределение mastery")
        dist = mastery_distribution(selected_class)
        fig = px.bar(
            dist, x="bucket", y="count",
            color="bucket",
            color_discrete_sequence=["#d62728", "#ff7f0e", "#ffdd57", "#88c999", "#2ca02c"][::-1],
            text="count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False,
            xaxis_title="Диапазон mastery",
            yaxis_title="Кол-во (ученик × навык)",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Проблемные навыки по классам")
    pivot = skill_class_pivot()
    fig = px.bar(
        pivot.melt(id_vars="skill", var_name="class", value_name="mastery"),
        x="skill", y="mastery", color="class",
        barmode="group",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(
        yaxis_range=[0, 1.1],
        xaxis_title="",
        yaxis_title="Средний mastery",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


# ─── Страница: Тепловая карта ────────────────────────────────

def render_heatmap():
    st.title("🔥 Тепловая карта")
    st.caption("Ученики × навыки. Зелёный — освоено, красный — проблема.")

    df = students_mastery_matrix(selected_class)
    if df.empty:
        st.warning("Нет данных.")
        return

    pivot = df.pivot_table(
        index=["class", "student"],
        columns="skill",
        values="mastery",
    )

    fig = px.imshow(
        pivot,
        color_continuous_scale=COLOR_SCALE,
        zmin=0, zmax=1,
        aspect="auto",
        text_auto=".2f",
    )
    fig.update_layout(
        height=max(400, len(pivot) * 22),
        xaxis_title="",
        yaxis_title="",
        coloraxis_colorbar=dict(title="Mastery"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    with st.expander("📋 Показать как таблицу"):
        st.dataframe(
            pivot.style.background_gradient(
                cmap="RdYlGn", axis=None, vmin=0, vmax=1
            ).format("{:.2f}", na_rep="—"),
            use_container_width=True,
        )

    download_button(
        pivot.reset_index(),
        "⬇️ Скачать CSV",
        f"heatmap_{selected_class}.csv",
    )


# ─── Страница: Проблемные темы ───────────────────────────────

def render_problems():
    st.title("⚠️ Проблемные темы")

    df = problems_by_class()
    if selected_class != "Все":
        df = df[df["class"] == selected_class]

    if df.empty:
        st.info("Нет данных.")
        return

    st.subheader("Рейтинг навыков по слабости")
    fig = px.bar(
        df.sort_values("avg_mastery"),
        x="avg_mastery", y="skill",
        color="class",
        orientation="h",
        barmode="group",
        range_x=[0, 1],
        color_discrete_sequence=px.colors.qualitative.Set2,
        text="avg_mastery",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=500, xaxis_title="Средний mastery", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Таблица по классам и навыкам")
    st.dataframe(
        df.style.background_gradient(
            subset=["avg_mastery"], cmap="RdYlGn", vmin=0, vmax=1
        ).format({"avg_mastery": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("🎯 Отстающие ученики")
    weak = weak_students()
    if selected_class != "Все":
        weak = weak[weak["class"] == selected_class]

    if weak.empty:
        st.success("Нет отстающих — все ученики выше порога 0.7")
    else:
        st.dataframe(
            weak.style.background_gradient(
                subset=["avg_mastery"], cmap="RdYlGn", vmin=0, vmax=1
            ).format({"avg_mastery": "{:.2f}"}),
            use_container_width=True,
            hide_index=True,
        )
        download_button(weak, "⬇️ Скачать список", "weak_students.csv")


# ─── Страница: Ученики ───────────────────────────────────────

def render_students():
    st.title("👤 Ученики")

    df = all_students(selected_class)
    if df.empty:
        st.info("Нет данных.")
        return

    min_mastery, max_mastery = st.slider(
        "Фильтр по среднему mastery",
        min_value=0.0, max_value=1.0,
        value=(0.0, 1.0), step=0.05,
    )
    filtered = df[
        (df["avg_mastery"] >= min_mastery) &
        (df["avg_mastery"] <= max_mastery)
    ]

    st.caption(f"Показано {len(filtered)} из {len(df)} учеников")

    st.dataframe(
        filtered.style.background_gradient(
            subset=["avg_mastery"], cmap="RdYlGn", vmin=0, vmax=1
        ).format({"avg_mastery": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    download_button(filtered, "⬇️ Скачать CSV", "students.csv")

    st.divider()
    st.subheader("📋 Детали по ученику")

    student_names = sorted(filtered["full_name"].tolist())
    selected_student = st.selectbox("Выберите ученика", student_names)

    if selected_student:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("**Mastery по навыкам**")
            detail = student_detail(selected_student)

            if not detail.empty:
                fig = px.bar(
                    detail.sort_values("mastery"),
                    x="mastery", y="skill",
                    orientation="h",
                    range_x=[0, 1],
                    color="mastery",
                    color_continuous_scale=COLOR_SCALE,
                    text="mastery",
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    height=max(250, len(detail) * 40),
                    showlegend=False,
                    coloraxis_showscale=False,
                    xaxis_title="Mastery",
                    yaxis_title="",
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**История ответов**")
            resp = student_responses(selected_student)
            if not resp.empty:
                resp_view = resp.copy()
                resp_view["correct"] = resp_view["correct"].map(
                    {True: "✅", False: "❌"}
                )
                st.dataframe(resp_view, use_container_width=True, hide_index=True)
            else:
                st.info("Нет ответов.")


# ─── Страница: Задания ───────────────────────────────────────

def render_tasks():
    st.title("📝 Задания")

    df = task_stats()
    if df.empty:
        st.info("Нет данных.")
        return

    st.subheader("Успешность заданий")
    fig = px.bar(
        df.sort_values("success_rate"),
        x="success_rate", y="code",
        orientation="h",
        range_x=[0, 1],
        color="success_rate",
        color_continuous_scale=COLOR_SCALE,
        text="success_rate",
        hover_data=["skill", "attempts", "correct"],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=max(300, len(df) * 30),
        showlegend=False,
        coloraxis_showscale=False,
        xaxis_title="Доля правильных",
        yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Детальная таблица")
    st.dataframe(
        df.style.background_gradient(
            subset=["success_rate"], cmap="RdYlGn", vmin=0, vmax=1
        ).format({"success_rate": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

    download_button(df, "⬇️ Скачать CSV", "task_stats.csv")


# ─── Страница: Создать тест ──────────────────────────────────

def render_generate_test():
    st.title("🎯 Создать тест")
    st.caption(
        "Выберите класс и тему — система подберёт **уникальный** набор "
        "заданий каждому ученику на основе его графа знаний."
    )

    tenant_id = "school_lyceum"
    user_id = "00000000-0000-0000-0000-000000000001"

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        class_name = st.selectbox(
            "Класс",
            ["10А", "10Б", "10Г"],
            key="gen_class",
        )

    with col2:
        topics = get_topics()
        if not topics:
            st.warning("Нет доступных тем. Загрузите таксономию.")
            return
        topic = st.selectbox("Тема", topics, key="gen_topic")

    with col3:
        n_tasks = st.number_input(
            "Заданий", min_value=2, max_value=10, value=5, key="gen_n"
        )

    if st.button("✨ Сгенерировать", type="primary"):
        with st.spinner("Подбираю задания..."):
            result = generate_for_class(class_name, topic, n_tasks, tenant_id)

        if "error" in result:
            st.error(result["error"])
            return

        st.session_state["generated_test"] = result
        st.rerun()

    if "generated_test" not in st.session_state:
        return

    result = st.session_state["generated_test"]
    st.divider()
    st.subheader(f"Превью: {result['class_name']} · «{result['topic']}»")
    st.caption(
        f"Каждому ученику — **свой** набор из {result['n_tasks']} заданий. "
        f"Всего сгенерировано: {len(result['students'])} персональных тестов."
    )

    # Сводная таблица
    summary = []
    for s in result["students"]:
        codes = ", ".join(t["code"] for t in s["tasks"])
        summary.append({
            "Ученик": s["full_name"],
            "Задания": codes or "—",
            "Кол-во": len(s["tasks"]),
        })
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

    # Детально по каждому ученику
    with st.expander("📋 Раскрыть все задания по ученикам"):
        for s in result["students"]:
            st.markdown(f"**{s['full_name']}**")
            for i, t in enumerate(s["tasks"], 1):
                st.markdown(
                    f"{i}. `[{t['code']}]` {t['text'][:100]}… "
                    f"— сложность {t['difficulty']:.2f}, "
                    f"mastery {t['mastery']:.2f}"
                )
            st.divider()

    st.divider()

    title = st.text_input(
        "Название теста",
        value=f"{result['topic']} — {result['class_name']}",
    )

    col_save, col_cancel = st.columns([1, 4])

    with col_save:
        if st.button("💾 Сохранить черновик"):
            group_id = get_group_id(result["class_name"], tenant_id)
            if not group_id:
                st.error(f"Не найден класс {result['class_name']}")
                return

            assignment_id = save_assignment(
                result, group_id, user_id, tenant_id, title
            )
            st.success(f"✅ Сохранено как черновик. ID: `{assignment_id[:8]}…`")
            st.balloons()

    with col_cancel:
        if st.button("🗑 Очистить"):
            st.session_state.pop("generated_test", None)
            st.rerun()


# ─── Роутинг ─────────────────────────────────────────────────

if page == "📊 Обзор":
    render_overview()
elif page == "🔥 Тепловая карта":
    render_heatmap()
elif page == "⚠️ Проблемные темы":
    render_problems()
elif page == "👤 Ученики":
    render_students()
elif page == "📝 Задания":
    render_tasks()
elif page == "🎯 Создать тест":
    render_generate_test()