CREATE TABLE public.feature
(
    symbol character varying,
    exchange character varying,
    feature character varying,
    date date,
    value_num double precision,
    value_text character varying,
    computed_at timestamp with time zone,
    PRIMARY KEY (symbol, exchange, feature, date)
)
WITH (
    OIDS = FALSE
);

CREATE INDEX feature_symbol_idx ON public.feature (symbol);
