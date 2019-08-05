CREATE TABLE public.feature
(
    feature text COLLATE pg_catalog."default" NOT NULL,
    value text COLLATE pg_catalog."default",
    CONSTRAINT feature_pkey PRIMARY KEY (feature)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.feature
    OWNER to postgres;