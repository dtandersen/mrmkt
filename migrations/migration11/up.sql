ALTER TABLE public.trigger ADD COLUMN name character varying;
UPDATE public.trigger SET name = 'trigger-' || LPAD(id::text, 6, '0') WHERE name IS NULL;
ALTER TABLE public.trigger ALTER COLUMN name SET NOT NULL;
ALTER TABLE public.trigger ADD CONSTRAINT trigger_name_unique UNIQUE (name);
