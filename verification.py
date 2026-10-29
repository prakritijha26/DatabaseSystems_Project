"""Logical data/schema fingerprint for the isolated Review 2 fixture database."""
import hashlib
import json
from engine import connect_database, TABLES
from psycopg import sql


def database_fingerprint():
    conn = connect_database()
    try:
        conn.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        snapshot = {}
        for table in sorted(TABLES | {'mark_change_log'}):
            rows = conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM public.{} t ORDER BY to_jsonb(t)::text').format(sql.Identifier(table))).fetchall()
            snapshot[table] = [r[0] for r in rows]
        for key, query in {
            'columns': "SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY 1,2",
            'views': "SELECT viewname,definition FROM pg_views WHERE schemaname='public' ORDER BY 1",
            'triggers': "SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2",
            'constraints': "SELECT c.relname,k.conname,pg_get_constraintdef(k.oid) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1,2",
            'sequences': "SELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY 1"
        }.items():
            snapshot[key] = conn.execute(query).fetchall()
        return hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()
