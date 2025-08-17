from django.db import models

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