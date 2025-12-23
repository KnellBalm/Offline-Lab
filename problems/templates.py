# problems/templates.py

def build_expected_sql(problem: dict) -> str:
    topic = problem.get("topic", "").lower()

    if topic == "retention":
        return """
        WITH cohort AS (
            SELECT
                user_id,
                date_trunc('day', signup_at) AS cohort_date
            FROM pa_users
        ),
        activity AS (
            SELECT
                c.cohort_date,
                date_part('day', e.event_time - c.cohort_date) AS day_n,
                COUNT(DISTINCT e.user_id)::float
                / COUNT(DISTINCT c.user_id) AS retention_rate
            FROM cohort c
            JOIN pa_events e USING (user_id)
            GROUP BY 1,2
        )
        SELECT cohort_date, day_n, retention_rate
        FROM activity
        WHERE day_n BETWEEN 0 AND 7
        ORDER BY cohort_date, day_n
        """

    if topic == "funnel":
        return """
        WITH v AS (
            SELECT DISTINCT user_id FROM pa_events WHERE event_name = 'view'
        ),
        c AS (
            SELECT DISTINCT user_id FROM pa_events WHERE event_name = 'add_to_cart'
        ),
        p AS (
            SELECT DISTINCT user_id FROM pa_events WHERE event_name = 'purchase'
        )
        SELECT
            COUNT(v.user_id) AS view_users,
            COUNT(c.user_id) AS cart_users,
            COUNT(p.user_id) AS purchase_users
        FROM v
        LEFT JOIN c USING (user_id)
        LEFT JOIN p USING (user_id)
        """

    if topic == "revenue":
        return """
        SELECT
            date_trunc('day', order_time) AS order_date,
            SUM(amount) AS revenue
        FROM pa_orders
        GROUP BY 1
        ORDER BY 1
        """

    if topic == "marketing":
        return """
        SELECT
            device,
            COUNT(DISTINCT user_id) AS users
        FROM pa_sessions
        GROUP BY 1
        ORDER BY users DESC
        LIMIT 10
        """

    if topic == "cohort":
        return """
        SELECT
            date_trunc('week', signup_at) AS cohort_week,
            COUNT(DISTINCT user_id) AS users
        FROM pa_users
        GROUP BY 1
        ORDER BY 1
        LIMIT 10
        """

    if topic == "segmentation":
        return """
        SELECT
            event_name,
            COUNT(DISTINCT user_id) AS users,
            COUNT(*) AS events
        FROM pa_events
        GROUP BY 1
        ORDER BY users DESC
        LIMIT 10
        """

    # 알 수 없는 topic은 기본 쿼리 반환 (에러 방지)
    return """
    SELECT 1 AS placeholder
    """

