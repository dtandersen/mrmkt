CREATE TABLE public.analysis
(
    symbol character varying,
    date date,
    net_income double precision,
    buffet_number double precision,
    price_to_book_value double precision,
    shares_outstanding bigint,
    liabilities double precision,
    assets double precision,
    margin_of_safety double precision,
    book_value double precision,
    eps double precision,
    equity double precision,
    pe double precision,
    PRIMARY KEY (symbol, date)
)
WITH (
    OIDS = FALSE
);
