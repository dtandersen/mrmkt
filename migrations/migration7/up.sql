CREATE TABLE public.ticker
(
    ticker character varying not null,
    exchange character varying not null,
    type character varying not null,
    PRIMARY KEY (ticker, exchange)
)
WITH (
    OIDS = FALSE
);
