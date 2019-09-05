CREATE TABLE public.financials
(
    symbol character varying not null,
    date date not null,
    data jsonb not null,
    PRIMARY KEY (symbol, date)
)
WITH (
    OIDS = FALSE
);
