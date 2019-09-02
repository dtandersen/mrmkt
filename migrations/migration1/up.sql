CREATE TABLE public.income_stmt
(
    symbol character varying,
    date date,
    net_income double precision,
    waso bigint,
    PRIMARY KEY (symbol, date)
)
WITH (
    OIDS = FALSE
);

CREATE TABLE public.balance_sheet
(
    symbol character varying,
    date date,
    total_assets double precision,
    total_liabilities double precision,
    PRIMARY KEY (symbol, date)
)
WITH (
    OIDS = FALSE
);
