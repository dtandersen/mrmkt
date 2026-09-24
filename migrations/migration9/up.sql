CREATE TABLE public.trigger
(
    id SERIAL PRIMARY KEY,
    symbol character varying not null,
    signal character varying not null,
    operator character varying not null,
    value double precision,
    frequency character varying not null,
    expires_at date,
    message character varying not null DEFAULT '',
    enabled boolean not null DEFAULT true,
    UNIQUE (symbol, signal, operator)
);

CREATE INDEX trigger_symbol_idx ON public.trigger (symbol);
CREATE INDEX trigger_enabled_idx ON public.trigger (enabled);
