# places/migrations/00XX_fix_routesnapshot_pk.py
from django.db import migrations, connection

DDL_CREATE_NEW = """
CREATE TABLE places_routesnapshot_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short VARCHAR(16) NOT NULL UNIQUE,
    params JSON NOT NULL,
    result JSON NOT NULL,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    view_count INTEGER NOT NULL DEFAULT 0
);
"""

SQL_COPY_DATA = """
INSERT INTO places_routesnapshot_new
(id, short, params, result, created_at, expires_at, view_count)
SELECT NULL, short, params, result, created_at, expires_at, COALESCE(view_count, 0)
FROM places_routesnapshot;
"""

SQL_DROP_OLD   = "DROP TABLE places_routesnapshot;"
SQL_RENAME_NEW = "ALTER TABLE places_routesnapshot_new RENAME TO places_routesnapshot;"

def forwards(apps, schema_editor):
    with connection.cursor() as cur:
        # 1) 테이블 존재 확인
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='places_routesnapshot'
        """)
        row = cur.fetchone()
        if not row:
            # 테이블 자체가 아직 없다면(로컬 초기 상태) 아무 것도 하지 않음
            return

        # 2) 현재 DDL 조회
        cur.execute("""
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='places_routesnapshot'
        """)
        ddl_row = cur.fetchone()
        ddl = (ddl_row[0] or "").upper() if ddl_row else ""

        # 이미 INTEGER PRIMARY KEY( AUTOINCREMENT )면 스킵
        if "PRIMARY KEY" in ddl and "INTEGER" in ddl:
            return

        # 3) 안전하게 외래키 비활성화(필요 시)
        cur.execute("PRAGMA foreign_keys=OFF;")

        # 4) 새 테이블 생성
        cur.execute(DDL_CREATE_NEW)

        # 5) 데이터 복사 (id는 새로 부여)
        cur.execute(SQL_COPY_DATA)

        # 6) 기존 테이블 교체
        cur.execute(SQL_DROP_OLD)
        cur.execute(SQL_RENAME_NEW)

        # 7) 외래키 재활성화
        cur.execute("PRAGMA foreign_keys=ON;")

def backwards(apps, schema_editor):
    # 역방향 필요 시 유사 로직으로 복구 가능. 여기서는 생략.
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('places', '0011_add_view_count_to_snapshot_fix'),  # ← 여기를 직전 마이그 번호로 바꾸세요 (showmigrations로 확인)
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

