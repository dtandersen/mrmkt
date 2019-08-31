CREATE TABLE public.daily_price
(
    symbol character varying,
    date character varying,
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
