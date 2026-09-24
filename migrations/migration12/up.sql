CREATE TABLE public.trigger_set
(
    name character varying PRIMARY KEY
);
CREATE TABLE public.trigger_set_member
(
    set_name character varying not null REFERENCES public.trigger_set (name) ON DELETE CASCADE,
    trigger_name character varying not null REFERENCES public.trigger (name) ON DELETE CASCADE,
    PRIMARY KEY (set_name, trigger_name)
);

CREATE INDEX trigger_set_member_trigger_idx ON public.trigger_set_member (trigger_name);
