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

-- ============================================================
-- SNOWFLAKE SCHEMA
-- ============================================================

DROP SCHEMA IF EXISTS snowflake CASCADE;
CREATE SCHEMA snowflake;


-- 1. Вимір товарів
CREATE TABLE snowflake.dim_product (
    product_key SERIAL PRIMARY KEY,
    stock_code TEXT NOT NULL UNIQUE,
    description TEXT
);


-- 2. Окремий вимір країн
CREATE TABLE snowflake.dim_country (
    country_key SERIAL PRIMARY KEY,
    country TEXT NOT NULL UNIQUE
);


-- 3. Вимір клієнтів
CREATE TABLE snowflake.dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id TEXT NOT NULL,
    country_key INTEGER NOT NULL
        REFERENCES snowflake.dim_country(country_key),

    UNIQUE (customer_id, country_key)
);


-- 4. Окремий вимір років
CREATE TABLE snowflake.dim_year (
    year_key SERIAL PRIMARY KEY,
    year_num SMALLINT NOT NULL UNIQUE
);


-- 5. Окремий вимір місяців
CREATE TABLE snowflake.dim_month (
    month_key SERIAL PRIMARY KEY,
    month_num SMALLINT NOT NULL,
    month_name TEXT NOT NULL,

    year_key INTEGER NOT NULL
        REFERENCES snowflake.dim_year(year_key),

    UNIQUE (month_num, year_key)
);


-- 6. Вимір дат
CREATE TABLE snowflake.dim_date (
    date_key SERIAL PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_num SMALLINT NOT NULL,

    month_key INTEGER NOT NULL
        REFERENCES snowflake.dim_month(month_key)
);


-- 7. Таблиця фактів
CREATE TABLE snowflake.fact_sales (
    sale_key BIGSERIAL PRIMARY KEY,

    invoice_no TEXT,

    product_key INTEGER NOT NULL
        REFERENCES snowflake.dim_product(product_key),

    customer_key INTEGER NOT NULL
        REFERENCES snowflake.dim_customer(customer_key),

    date_key INTEGER NOT NULL
        REFERENCES snowflake.dim_date(date_key),

    quantity INTEGER,
    unit_price NUMERIC(14, 4),
    total_amount NUMERIC(18, 4)
);


-- ============================================================
-- ЗАПОВНЕННЯ DIM_PRODUCT
-- ============================================================

INSERT INTO snowflake.dim_product (
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
-- ЗАПОВНЕННЯ DIM_COUNTRY
-- ============================================================

INSERT INTO snowflake.dim_country (
    country
)
SELECT DISTINCT
    COALESCE(country, 'Unknown')
FROM public.online_retail;


-- ============================================================
-- ЗАПОВНЕННЯ DIM_CUSTOMER
-- ============================================================

INSERT INTO snowflake.dim_customer (
    customer_id,
    country_key
)
SELECT DISTINCT
    CASE
        WHEN r.customer_id IS NULL
            THEN 'UNKNOWN'
        ELSE r.customer_id::bigint::text
    END,

    c.country_key

FROM public.online_retail r

JOIN snowflake.dim_country c
    ON c.country = COALESCE(r.country, 'Unknown');


-- ============================================================
-- ЗАПОВНЕННЯ DIM_YEAR
-- ============================================================

INSERT INTO snowflake.dim_year (
    year_num
)
SELECT DISTINCT
    EXTRACT(YEAR FROM invoice_date)::smallint
FROM public.online_retail
WHERE invoice_date IS NOT NULL;


-- ============================================================
-- ЗАПОВНЕННЯ DIM_MONTH
-- ============================================================

INSERT INTO snowflake.dim_month (
    month_num,
    month_name,
    year_key
)
SELECT DISTINCT
    EXTRACT(MONTH FROM r.invoice_date)::smallint,
    TO_CHAR(r.invoice_date, 'Month'),
    y.year_key

FROM public.online_retail r

JOIN snowflake.dim_year y
    ON y.year_num =
       EXTRACT(YEAR FROM r.invoice_date)::smallint

WHERE r.invoice_date IS NOT NULL;


-- ============================================================
-- ЗАПОВНЕННЯ DIM_DATE
-- ============================================================

INSERT INTO snowflake.dim_date (
    full_date,
    day_num,
    month_key
)
SELECT DISTINCT
    r.invoice_date::date,

    EXTRACT(DAY FROM r.invoice_date)::smallint,

    m.month_key

FROM public.online_retail r

JOIN snowflake.dim_year y
    ON y.year_num =
       EXTRACT(YEAR FROM r.invoice_date)::smallint

JOIN snowflake.dim_month m
    ON m.year_key = y.year_key

    AND m.month_num =
        EXTRACT(MONTH FROM r.invoice_date)::smallint

WHERE r.invoice_date IS NOT NULL;


-- ============================================================
-- ЗАПОВНЕННЯ FACT_SALES
-- ============================================================

INSERT INTO snowflake.fact_sales (
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

JOIN snowflake.dim_product p
    ON p.stock_code = r.stock_code::text

JOIN snowflake.dim_country co
    ON co.country = COALESCE(r.country, 'Unknown')

JOIN snowflake.dim_customer c
    ON c.country_key = co.country_key

    AND c.customer_id =
        CASE
            WHEN r.customer_id IS NULL
                THEN 'UNKNOWN'
            ELSE r.customer_id::bigint::text
        END

JOIN snowflake.dim_date d
    ON d.full_date = r.invoice_date::date;


-- ============================================================
-- ІНДЕКСИ
-- ============================================================

CREATE INDEX idx_snow_fact_product
ON snowflake.fact_sales(product_key);

CREATE INDEX idx_snow_fact_customer
ON snowflake.fact_sales(customer_key);

CREATE INDEX idx_snow_fact_date
ON snowflake.fact_sales(date_key);

CREATE INDEX idx_snow_customer_country
ON snowflake.dim_customer(country_key);

CREATE INDEX idx_snow_date_month
ON snowflake.dim_date(month_key);

CREATE INDEX idx_snow_month_year
ON snowflake.dim_month(year_key);


-- ============================================================
-- ПЕРЕВІРКА
-- ============================================================

SELECT COUNT(*)
FROM snowflake.fact_sales;

SELECT COUNT(*)
FROM snowflake.dim_product;

SELECT COUNT(*)
FROM snowflake.dim_country;

SELECT COUNT(*)
FROM snowflake.dim_customer;

SELECT COUNT(*)
FROM snowflake.dim_year;

SELECT COUNT(*)
FROM snowflake.dim_month;

SELECT COUNT(*)
FROM snowflake.dim_date;