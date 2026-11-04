from pathlib import Path
import os
import time
from statistics import median

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


# ------------------------------------------------------------
# ПІДКЛЮЧЕННЯ ДО POSTGRESQL
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# .env знаходиться в корені lab1
load_dotenv(PROJECT_DIR / ".env")

db_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("PGUSER", "postgres"),
    password=os.getenv("PGPASSWORD"),
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    database=os.getenv("PGDATABASE", "analytics_lab"),
)

engine = create_engine(db_url)


# ------------------------------------------------------------
# АНАЛІТИЧНІ ЗАПИТИ
# ------------------------------------------------------------

QUERIES = {
    "revenue_by_country": {

        "star": """
            SELECT
                c.country,
                SUM(f.total_amount) AS revenue
            FROM star.fact_sales f
            JOIN star.dim_customer c
                ON c.customer_key = f.customer_key
            WHERE f.quantity > 0
              AND f.unit_price > 0
            GROUP BY c.country
            ORDER BY revenue DESC;
        """,

        "snowflake": """
            SELECT
                co.country,
                SUM(f.total_amount) AS revenue
            FROM snowflake.fact_sales f
            JOIN snowflake.dim_customer c
                ON c.customer_key = f.customer_key
            JOIN snowflake.dim_country co
                ON co.country_key = c.country_key
            WHERE f.quantity > 0
              AND f.unit_price > 0
            GROUP BY co.country
            ORDER BY revenue DESC;
        """
    },


    "monthly_revenue": {

        "star": """
            SELECT
                d.year_num,
                d.month_num,
                SUM(f.total_amount) AS revenue
            FROM star.fact_sales f
            JOIN star.dim_date d
                ON d.date_key = f.date_key
            WHERE f.quantity > 0
              AND f.unit_price > 0
            GROUP BY d.year_num, d.month_num
            ORDER BY d.year_num, d.month_num;
        """,

        "snowflake": """
            SELECT
                y.year_num,
                m.month_num,
                SUM(f.total_amount) AS revenue
            FROM snowflake.fact_sales f
            JOIN snowflake.dim_date d
                ON d.date_key = f.date_key
            JOIN snowflake.dim_month m
                ON m.month_key = d.month_key
            JOIN snowflake.dim_year y
                ON y.year_key = m.year_key
            WHERE f.quantity > 0
              AND f.unit_price > 0
            GROUP BY y.year_num, m.month_num
            ORDER BY y.year_num, m.month_num;
        """
    },


    "top_10_products": {

        "star": """
            SELECT
                p.stock_code,
                p.description,
                SUM(f.total_amount) AS revenue
            FROM star.fact_sales f
            JOIN star.dim_product p
                ON p.product_key = f.product_key
            WHERE f.quantity > 0
              AND f.unit_price > 0
            GROUP BY p.stock_code, p.description
            ORDER BY revenue DESC
            LIMIT 10;
        """,

        "snowflake": """
            SELECT
                p.stock_code,
                p.description,
                SUM(f.total_amount) AS revenue
            FROM snowflake.fact_sales f
            JOIN snowflake.dim_product p
                ON p.product_key = f.product_key
            WHERE f.quantity > 0
              AND f.unit_price > 0
            GROUP BY p.stock_code, p.description
            ORDER BY revenue DESC
            LIMIT 10;
        """
    }
}


# ------------------------------------------------------------
# ВИМІРЮВАННЯ ЧАСУ
# ------------------------------------------------------------

def benchmark_query(sql, repeats=5):

    times = []

    # Перший прогрівальний запуск
    with engine.connect() as connection:
        connection.execute(text(sql)).fetchall()

    result = None

    for _ in range(repeats):

        start = time.perf_counter()

        with engine.connect() as connection:
            result = connection.execute(text(sql)).fetchall()

        end = time.perf_counter()

        times.append(end - start)

    return median(times), result


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print("========== LABORATORY WORK 2 ==========\n")

    # Перевірка БД і кількості записів
    with engine.connect() as connection:

        database = connection.execute(
            text("SELECT current_database();")
        ).scalar()

        source_rows = connection.execute(
            text("SELECT COUNT(*) FROM public.online_retail;")
        ).scalar()

        star_rows = connection.execute(
            text("SELECT COUNT(*) FROM star.fact_sales;")
        ).scalar()

        snowflake_rows = connection.execute(
            text("SELECT COUNT(*) FROM snowflake.fact_sales;")
        ).scalar()

    print(f"Database: {database}")
    print(f"Source rows:    {source_rows:,}")
    print(f"Star rows:      {star_rows:,}")
    print(f"Snowflake rows: {snowflake_rows:,}")
    print()

    results = []

    for query_name, query_versions in QUERIES.items():

        print(f"--- {query_name} ---")

        star_time, star_result = benchmark_query(
            query_versions["star"]
        )

        snowflake_time, snowflake_result = benchmark_query(
            query_versions["snowflake"]
        )

        print(
            f"Star:      {star_time:.6f} seconds"
        )

        print(
            f"Snowflake: {snowflake_time:.6f} seconds"
        )

        # Перевіряємо, що обидві схеми повертають однаковий результат
        same_result = star_result == snowflake_result

        print(
            f"Same result: {same_result}"
        )

        speed_ratio = (
            snowflake_time / star_time
            if star_time > 0
            else 0
        )

        print(
            f"Snowflake / Star time: {speed_ratio:.2f}x"
        )

        print()

        results.append({
            "query": query_name,
            "star_seconds": star_time,
            "snowflake_seconds": snowflake_time,
            "snowflake_div_star": speed_ratio,
            "same_result": same_result
        })


    # --------------------------------------------------------
    # ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТІВ
    # --------------------------------------------------------

    df = pd.DataFrame(results)

    print("========== RESULTS ==========")

    print(
        df.to_string(index=False)
    )

    output_file = (
        OUTPUT_DIR
        / "lab2_benchmark_results.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nResults saved to:\n{output_file}"
    )


if __name__ == "__main__":
    main()