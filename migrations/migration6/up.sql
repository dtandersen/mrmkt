CREATE TABLE public.enterprise_value
(
    symbol character varying not null,
    date date not null,
    stock_price double precision,
    shares_outstanding double precision,
    market_cap double precision,
    PRIMARY KEY (symbol, date)
)
WITH (
    OIDS = FALSE
);
