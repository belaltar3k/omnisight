FROM postgres:15

# Install pg_cron for scheduled background jobs directly in PostgreSQL
RUN apt-get update && apt-get -y install postgresql-15-cron && \
    rm -rf /var/lib/apt/lists/*

# Add custom postgres configuration that preloads pg_cron
COPY config/postgresql.conf /etc/postgresql/postgresql.conf

# Add initialization scripts
COPY initdb/ /docker-entrypoint-initdb.d/

# Override entrypoint parameter to use our custom config
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
