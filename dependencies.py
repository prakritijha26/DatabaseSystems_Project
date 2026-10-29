"""Catalog-recorded reverse dependencies; does not infer dynamic SQL references."""


def find_broken_dependencies(conn, table_name: str, column_name: str = None) -> list[dict]:
    """Inspect a public relation, optionally a column, without changing catalogs."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.oid, a.attnum
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_attribute a ON a.attrelid = c.oid
                AND a.attname = %s AND a.attnum > 0 AND NOT a.attisdropped
            WHERE n.nspname = 'public' AND c.relname = %s AND c.relkind IN ('r', 'p')
        """, (column_name, table_name))
        target = cur.fetchone()
        if target is None or (column_name is not None and target[1] is None):
            raise ValueError("Unknown public table or column.")
        oid, attnum = target
        cur.execute("""
            WITH RECURSIVE impacted(oid, path) AS (
                SELECT %s::oid, ARRAY[%s::oid]
                UNION ALL
                SELECT v.oid, i.path || v.oid
                FROM impacted i
                JOIN pg_depend d ON d.refclassid = 'pg_class'::regclass
                    AND d.refobjid = i.oid
                JOIN pg_rewrite r ON d.classid = 'pg_rewrite'::regclass AND r.oid = d.objid
                JOIN pg_class v ON v.oid = r.ev_class AND v.relkind IN ('v', 'm')
                WHERE NOT v.oid = ANY(i.path)
                  AND (i.oid <> %s::oid OR %s::smallint IS NULL OR d.refobjsubid = %s)
            )
            SELECT DISTINCT n.nspname || '.' || c.relname, 'VIEW'
            FROM impacted i JOIN pg_class c ON c.oid = i.oid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.oid <> %s::oid
            UNION
            SELECT DISTINCT n.nspname || '.' || t.tgname, 'TRIGGER'
            FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_depend d ON d.classid = 'pg_trigger'::regclass AND d.objid = t.oid
                AND d.refclassid = 'pg_class'::regclass AND d.refobjid = %s::oid
            WHERE NOT t.tgisinternal AND (%s::smallint IS NULL OR d.refobjsubid = %s)
            UNION
            SELECT DISTINCT n.nspname || '.' || c.relname || '.' || k.conname, 'CONSTRAINT'
            FROM pg_constraint k JOIN pg_class c ON c.oid = k.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE k.contype = 'f' AND (
                (k.conrelid = %s::oid AND (%s::smallint IS NULL OR %s = ANY(k.conkey))) OR
                (k.confrelid = %s::oid AND (%s::smallint IS NULL OR %s = ANY(k.confkey))))
            ORDER BY 2, 1
        """, (oid, oid, oid, attnum, attnum, oid, oid, attnum, attnum,
              oid, attnum, attnum, oid, attnum, attnum))
        subject = f"public.{table_name}" + (f".{column_name}" if column_name else "")
        return [{"object_name": name, "object_type": kind,
                 "reason": f"Catalog-recorded dependency on {subject}; affected by its removal.",
                 "severity": "TRIGGER_INVALIDATED" if kind == "TRIGGER" else "CRITICAL_BREAK"}
                for name, kind in cur.fetchall()]
