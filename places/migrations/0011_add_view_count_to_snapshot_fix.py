# places/migrations/0011_add_view_count_to_snapshot_fix.py
from django.db import migrations

SQL_ADD_COL = """
-- 컬럼이 없을 때만 추가 (SQLite)
PRAGMA foreign_keys=off;
CREATE TABLE IF NOT EXISTS __tmp_check (x INT);
DROP TABLE __tmp_check;

-- 컬럼 존재 여부 검사 후 없으면 추가
-- (SQLite는 IF NOT EXISTS가 컬럼 추가에 직접 지원되지 않아 pragma로 분기)
"""

SQL_ADD_COL += """
-- pragma_table_info 결과에 view_count가 없을 때만 ALTER 실행
-- Django RunSQL에서는 조건 분기가 어려워서, 안전하게 바로 시도하고
-- 이미 있으면 에러 없이 지나가도록 하는 방식이 필요합니다.
-- 다만 SQLite는 같은 컬럼이 있으면 에러가 나므로, 먼저 검사 후 실행하는 트릭을 씁니다.
"""

SQL_ADD_COL += """
-- 검사 결과를 이용해 동적으로 실행하는 건 SQLite의 pure SQL에서 제한적이라
-- 여기서는 '없다고 가정'하고 추가를 시도하고, 실패하면 그냥 무시하는 방향을 택합니다.
"""

SQL_ALTER = """
ALTER TABLE places_routesnapshot
ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0;
"""

def forwards(apps, schema_editor):
    from django.db import connection
    with connection.cursor() as cur:
        # 이미 있으면 아무 것도 안 함
        cur.execute("PRAGMA table_info(places_routesnapshot)")
        cols = [r[1] for r in cur.fetchall()]
        if "view_count" in cols:
            return
        # 없으면 추가
        cur.execute(SQL_ALTER)

def backwards(apps, schema_editor):
    # SQLite는 오래된 버전에선 DROP COLUMN 미지원. 되돌림은 no-op 처리.
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('places', '0010_routesnapshot'),  # 직전 마이그레이션 이름으로 바꿔줘!
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
