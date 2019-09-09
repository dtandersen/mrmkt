dbschema.yml
```
databases:
    db1: # Unique tag
        engine: postgresql # Engine name (`postgresql` pr `mysql`)
        host: 127.0.0.1 # Database host
        port: 5432 # Database port
        user: postgres # Username
        password: local # Optional password
        db: mrmkt # Database name
        path: migrations
        pre_migration: '' # Optional queries ran before migrating
        post_migration: '' # 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gab; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gab' # Optional queries ran after migrating
```

dbschema -c dbschema.yml