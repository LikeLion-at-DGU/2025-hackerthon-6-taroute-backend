import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets

class Place(models.Model):
  id = models.AutoField(primary_key=True)
  gplace_id = models.CharField(max_length=100, null=True, blank=True)
  name = models.CharField(max_length=50)
  address = models.CharField(max_length=50)
  dong = models.CharField(max_length=50)
  longitude = models.FloatField()
  latitude = models.FloatField()
  number = models.CharField(max_length=50)
  running_time = models.CharField(max_length=50)
  place_url = models.TextField(null=True, blank=True)
  created_at = models.DateTimeField(auto_now_add=True)

  # 인기순에는 장소의 위도경도이름을 보고 우리꺼랑 대조해서 일치하면 카운트를 가져와가지고 정렬 [구글-우리DB]

class PopularKeyward(models.Model):
  place_id = models.CharField(max_length=100, unique=True)
  place_name = models.CharField(max_length=50)
  click_num = models.IntegerField(default=1)

class SubwayLines(models.Model):
  id = models.AutoField(primary_key=True)
  line = models.CharField(max_length=50)
  station = models.CharField(max_length=50)
  longitude = models.FloatField()
  latitude = models.FloatField()

def gen_short(n=8):
    # URL-safe 랜덤 토큰 일부만 사용 (짧게)
    return secrets.token_urlsafe(6)[:n]

def default_expires(): 
    # 7일 만료
    return timezone.now() + timedelta(days=7)

def gen_uuid_hex():
    return uuid.uuid4().hex

class RouteSnapshot(models.Model):
    # short + unique index
    id = models.CharField(primary_key=True,max_length=32,default=gen_uuid_hex,editable=False)
    short = models.CharField(max_length=16, unique=True, db_index=True, default=gen_short)
    params = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expires)
    view_count = models.PositiveIntegerField(default=0)

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = gen_uuid_hex()
        super().save(*args, **kwargs)