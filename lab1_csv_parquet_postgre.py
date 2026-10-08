from pathlib import Path
import os
import re
import time
from statistics import median

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CSV_PATH = BASE_DIR / "data" / "online_retail_II.csv"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

COLUMN_MAP = {
    "invoice": "invoice_no",
    "invoiceno": "invoice_no",
    "stockcode": "stock_code",
    "description": "description",
    "quantity": "quantity",
    "invoicedate": "invoice_date",
    "price": "price",
    "unitprice": "price",
    "customerid": "customer_id",
    "country": "country",
}


def normalized_key(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def standardize_columns(df):
    rename_dict = {}

    for column in df.columns:
        key = normalized_key(column)

        if key in COLUMN_MAP:
            rename_dict[column] = COLUMN_MAP[key]

    df = df.rename(columns=rename_dict)

    required_columns = {
        "quantity",
        "price",
        "country"
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"У CSV немає необхідних колонок: {missing}\n"
            f"Знайдені колонки: {list(df.columns)}"
        )

    return df


def prepare_dataframe(df):
    df = standardize_columns(df)

    # Перетворення числових колонок
    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    # Перетворення дати
    if "invoice_date" in df.columns:
        df["invoice_date"] = pd.to_datetime(
            df["invoice_date"],
            errors="coerce"
        )


    df["total_amount"] = (
        df["quantity"] * df["price"]
    )

    return df


def file_size_mb(path):
    return path.stat().st_size / (1024 ** 2)


# ============================================================
# ВИМІРЮВАННЯ ЧАСУ
# ============================================================

def benchmark(function, repeats=3):

    times = []
    result = None

    for i in range(repeats):

        start = time.perf_counter()

        result = function()

        end = time.perf_counter()

        times.append(end - start)

    return median(times), result


# ============================================================
# ПОШУК ОРИГІНАЛЬНИХ НАЗВ КОЛОНОК CSV
# ============================================================

def find_original_columns(csv_path):

    header = pd.read_csv(
        csv_path,
        nrows=0
    )

    found = {}

    for column in header.columns:

        key = normalized_key(column)

        if key in COLUMN_MAP:
            found[COLUMN_MAP[key]] = column

    needed = {
        "quantity",
        "price",
        "country"
    }

    missing = needed - set(found)

    if missing:
        raise ValueError(
            f"Не знайдені колонки: {missing}"
        )

    return found


# ============================================================
# АНАЛІТИЧНИЙ ЗАПИТ ДО CSV
# ============================================================

def csv_query():

    original = find_original_columns(
        CSV_PATH
    )

    usecols = [
        original["quantity"],
        original["price"],
        original["country"]
    ]

    df = pd.read_csv(
        CSV_PATH,
        usecols=usecols,
        low_memory=False
    )

    df = standardize_columns(df)

    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    df = df[
        (df["country"] == "United Kingdom")
        & (df["quantity"] > 0)
        & (df["price"] > 0)
    ].copy()

    total_sales = (
        df["quantity"] * df["price"]
    ).sum()

    return total_sales


# ============================================================
# АНАЛІТИЧНИЙ ЗАПИТ ДО PARQUET
# ============================================================

def parquet_query(parquet_path):

    df = pd.read_parquet(
        parquet_path,

        columns=[
            "quantity",
            "price",
            "country"
        ],

        filters=[
            (
                "country",
                "==",
                "United Kingdom"
            )
        ],

        engine="pyarrow"
    )

    df = df[
        (df["quantity"] > 0)
        & (df["price"] > 0)
    ].copy()

    total_sales = (
        df["quantity"] * df["price"]
    ).sum()

    return total_sales


# ============================================================
# POSTGRESQL
# ============================================================

def connect_to_postgresql(df):

    load_dotenv(
        BASE_DIR / ".env"
    )

    password = os.getenv(
        "PGPASSWORD"
    )

    if not password:

        print(
            "\nPostgreSQL не підключено."
        )

        return

    db_url = URL.create(

        drivername="postgresql+psycopg",

        username=os.getenv(
            "PGUSER",
            "postgres"
        ),

        password=password,

        host=os.getenv(
            "PGHOST",
            "localhost"
        ),

        port=int(
            os.getenv(
                "PGPORT",
                "5432"
            )
        ),

        database=os.getenv(
            "PGDATABASE",
            "analytics_lab"
        )
    )

    engine = create_engine(
        db_url
    )

    # Перевіряємо підключення
    with engine.connect() as connection:

        version = connection.execute(
            text("SELECT version();")
        ).scalar()

        print(
            "\nPostgreSQL підключено успішно!"
        )

        print(version)

    load_data = os.getenv(
        "POSTGRES_LOAD",
        "false"
    )

    if load_data.lower() == "true":

        print(
            "\nЗавантаження даних "
            "у PostgreSQL..."
        )

        df.to_sql(

            "online_retail",

            engine,

            if_exists="replace",

            index=False,

            chunksize=10000
        )

        with engine.connect() as connection:

            count = connection.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM online_retail;"
                )
            ).scalar()

        print(
            f"Завантажено {count:,} рядків."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "========== LABORATORY WORK 1 =========="
    )

    # --------------------------------------------------------
    # 1. Перевірка CSV
    # --------------------------------------------------------

    if not CSV_PATH.exists():

        raise FileNotFoundError(

            f"\nФайл не знайдений:\n"
            f"{CSV_PATH}\n\n"
        )

    # --------------------------------------------------------
    # 2. Зчитування CSV
    # --------------------------------------------------------

    print(
        "\n1. Reading CSV..."
    )

    df = pd.read_csv(
        CSV_PATH,
        low_memory=False
    )

    df = prepare_dataframe(df)

    print(
        f"Rows: {len(df):,}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print(
        "\nData types:"
    )

    print(
        df.dtypes
    )

    print(
        "\nFirst rows:"
    )

    print(
        df.head()
    )

    # --------------------------------------------------------
    # 3. Розмір CSV
    # --------------------------------------------------------

    csv_size = file_size_mb(
        CSV_PATH
    )

    print(
        f"\nCSV size: "
        f"{csv_size:.2f} MB"
    )

    # --------------------------------------------------------
    # 4. CSV -> PARQUET
    # --------------------------------------------------------

    print(
        "\n2. Creating Parquet files..."
    )

    compression_options = {

        "uncompressed": None,

        "snappy": "snappy",

        "gzip": "gzip",

        "zstd": "zstd"
    }

    parquet_paths = {}

    for label, compression in compression_options.items():

        path = (
            OUTPUT_DIR
            / f"online_retail_{label}.parquet"
        )

        df.to_parquet(

            path,

            engine="pyarrow",

            compression=compression,

            index=False
        )

        parquet_paths[label] = path

        size = file_size_mb(
            path
        )

        print(
            f"{label:12s}: "
            f"{size:.2f} MB"
        )

    # --------------------------------------------------------
    # 5. BENCHMARK CSV
    # --------------------------------------------------------

    print(
        "\n3. Performance test..."
    )

    csv_time, csv_result = benchmark(
        csv_query,
        repeats=3
    )

    print(
        f"\nCSV:"
    )

    print(
        f"Time = {csv_time:.4f} seconds"
    )

    print(
        f"Result = {csv_result:.2f}"
    )

    # --------------------------------------------------------
    # 6. Таблиця результатів
    # --------------------------------------------------------

    rows = [

        {
            "format": "CSV",

            "compression": "-",

            "size_mb": csv_size,

            "compression_ratio_vs_csv": 1.0,

            "median_query_seconds": csv_time,

            "speedup_vs_csv": 1.0,

            "query_result": csv_result
        }

    ]

    # --------------------------------------------------------
    # 7. BENCHMARK PARQUET
    # --------------------------------------------------------

    for label, path in parquet_paths.items():

        query_time, result = benchmark(

            lambda p=path:
                parquet_query(p),

            repeats=3
        )

        size = file_size_mb(
            path
        )

        compression_ratio = (
            csv_size / size
        )

        speedup = (
            csv_time / query_time
        )

        rows.append(

            {
                "format": "Parquet",

                "compression": label,

                "size_mb": size,

                "compression_ratio_vs_csv":
                    compression_ratio,

                "median_query_seconds":
                    query_time,

                "speedup_vs_csv":
                    speedup,

                "query_result":
                    result
            }

        )

        print(
            f"\nParquet {label}:"
        )

        print(
            f"Size = {size:.2f} MB"
        )

        print(
            f"Time = {query_time:.4f} seconds"
        )

        print(
            f"Compression ratio = "
            f"{compression_ratio:.2f}x"
        )

        print(
            f"Speedup = "
            f"{speedup:.2f}x"
        )

    # --------------------------------------------------------
    # 8. ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТІВ
    # --------------------------------------------------------

    results = pd.DataFrame(
        rows
    )

    results_path = (
        OUTPUT_DIR
        / "benchmark_results.csv"
    )

    results.to_csv(
        results_path,
        index=False
    )

    print(
        "\n========== RESULTS =========="
    )

    print(
        results.to_string(
            index=False
        )
    )

    print(
        "\nResults saved to:"
    )

    print(
        results_path
    )

    # --------------------------------------------------------
    # 9. PostgreSQL
    # --------------------------------------------------------

    print(
        "\n4. PostgreSQL connection..."
    )

    connect_to_postgresql(
        df
    )


if __name__ == "__main__":
    main()