CREATE TABLE public.cash_flow
(
    symbol character varying not null,
    date date not null,
    operating_cash_flow double precision,
    capital_expenditure double precision,
    free_cash_flow double precision,
    dividend_payments double precision,
    PRIMARY KEY (symbol, date)
)
WITH (
    OIDS = FALSE
);
