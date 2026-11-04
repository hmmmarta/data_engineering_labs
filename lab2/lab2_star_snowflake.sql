-- ============================================================
-- LAB 2
-- STAR SCHEMA
-- Source table: public.online_retail
-- ============================================================

DROP SCHEMA IF EXISTS star CASCADE;
CREATE SCHEMA star;


-- 1. Вимір товарів
CREATE TABLE star.dim_product (
    product_key SERIAL PRIMARY KEY,
    stock_code TEXT NOT NULL UNIQUE,
    description TEXT
);


-- 2. Вимір клієнтів
CREATE TABLE star.dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id TEXT NOT NULL,
    country TEXT NOT NULL,
    UNIQUE (customer_id, country)
);


-- 3. Вимір дат
CREATE TABLE star.dim_date (
    date_key SERIAL PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_num SMALLINT NOT NULL,
    month_num SMALLINT NOT NULL,
    month_name TEXT NOT NULL,
    quarter_num SMALLINT NOT NULL,
    year_num SMALLINT NOT NULL
);


-- 4. Таблиця фактів
CREATE TABLE star.fact_sales (
    sale_key BIGSERIAL PRIMARY KEY,

    invoice_no TEXT,

    product_key INTEGER NOT NULL
        REFERENCES star.dim_product(product_key),

    customer_key INTEGER NOT NULL
        REFERENCES star.dim_customer(customer_key),

    date_key INTEGER NOT NULL
        REFERENCES star.dim_date(date_key),

    quantity INTEGER,
    unit_price NUMERIC(14, 4),
    total_amount NUMERIC(18, 4)
);


-- ============================================================
-- ЗАПОВНЕННЯ DIM_PRODUCT
-- ============================================================

INSERT INTO star.dim_product (
    stock_code,
    description
)
SELECT
    stock_code::text,
    MIN(COALESCE(description, 'Unknown'))
FROM public.online_retail
WHERE stock_code IS NOT NULL
GROUP BY stock_code;


-- ============================================================
-- ЗАПОВНЕННЯ DIM_CUSTOMER
-- ============================================================

INSERT INTO star.dim_customer (
    customer_id,
    country
)
SELECT DISTINCT
    CASE
        WHEN customer_id IS NULL
            THEN 'UNKNOWN'
        ELSE customer_id::bigint::text
    END,

    COALESCE(country, 'Unknown')

FROM public.online_retail;


-- ============================================================
-- ЗАПОВНЕННЯ DIM_DATE
-- ============================================================

INSERT INTO star.dim_date (
    full_date,
    day_num,
    month_num,
    month_name,
    quarter_num,
    year_num
)
SELECT DISTINCT
    invoice_date::date,

    EXTRACT(DAY FROM invoice_date)::smallint,

    EXTRACT(MONTH FROM invoice_date)::smallint,

    TO_CHAR(invoice_date, 'Month'),

    EXTRACT(QUARTER FROM invoice_date)::smallint,

    EXTRACT(YEAR FROM invoice_date)::smallint

FROM public.online_retail

WHERE invoice_date IS NOT NULL;


-- ============================================================
-- ЗАПОВНЕННЯ FACT_SALES
-- ============================================================

INSERT INTO star.fact_sales (
    invoice_no,
    product_key,
    customer_key,
    date_key,
    quantity,
    unit_price,
    total_amount
)
SELECT
    r.invoice_no::text,

    p.product_key,

    c.customer_key,

    d.date_key,

    r.quantity,

    r.price::numeric(14, 4),

    (r.quantity * r.price)::numeric(18, 4)

FROM public.online_retail r

JOIN star.dim_product p
    ON p.stock_code = r.stock_code::text

JOIN star.dim_customer c
    ON c.customer_id =
        CASE
            WHEN r.customer_id IS NULL
                THEN 'UNKNOWN'
            ELSE r.customer_id::bigint::text
        END

    AND c.country = COALESCE(r.country, 'Unknown')

JOIN star.dim_date d
    ON d.full_date = r.invoice_date::date;


-- ============================================================
-- ІНДЕКСИ
-- ============================================================

CREATE INDEX idx_star_fact_product
ON star.fact_sales(product_key);

CREATE INDEX idx_star_fact_customer
ON star.fact_sales(customer_key);

CREATE INDEX idx_star_fact_date
ON star.fact_sales(date_key);


-- ============================================================
-- ПЕРЕВІРКА
-- ============================================================

SELECT COUNT(*)
FROM public.online_retail;

SELECT COUNT(*)
FROM star.fact_sales;

SELECT COUNT(*)
FROM star.dim_product;

SELECT COUNT(*)
FROM star.dim_customer;

SELECT COUNT(*)
FROM star.dim_date;