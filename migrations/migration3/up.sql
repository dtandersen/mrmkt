CREATE TABLE public.daily_price
(
    symbol character varying,
    date date,
    open double precision,
    close double precision,
    high double precision,
    low double precision,
    volume double precision,
    PRIMARY KEY (symbol, date)
)
WITH (
    OIDS = FALSE
);
