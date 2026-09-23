CREATE TABLE public.ticker_tag
(
    ticker character varying not null,
    exchange character varying not null,
    tag character varying not null,
    PRIMARY KEY (ticker, exchange, tag),
    FOREIGN KEY (ticker, exchange)
        REFERENCES public.ticker (ticker, exchange)
        ON DELETE CASCADE
);

CREATE INDEX ticker_tag_tag_idx ON public.ticker_tag (tag);
