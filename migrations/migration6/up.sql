CREATE TABLE public.cash_flow
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
