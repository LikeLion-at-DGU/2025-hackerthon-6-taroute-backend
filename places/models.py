from django.db import models

def image_upload_path(instance, filename):
  return f'{instance.pk}/{filename}'

class Place(models.Model):
  id = models.AutoField(primary_key=True)
  name = models.CharField(max_length=50)
  address = models.CharField(max_length=50)
  dong = models.CharField(max_length=50)
  longitude = models.FloatField()
  latitude = models.FloatField()
  number = models.CharField(max_length=50)
  running_time = models.CharField(max_length=50)
  place_image = models.ImageField(upload_to=image_upload_path, blank=True, null=True)
  # category = models.ForeignKey()
  # place_total_count

class Review(models.Model):
  id = models.AutoField(primary_key=True)
  place = models.ForeignKey(Place, on_delete=models.CASCADE)
  review_content = models.TextField()
  review_score = models.DecimalField(max_digits=2, decimal_places=1)
  ai_review = models.TextField(null=True)
  review_image = models.ImageField(upload_to=image_upload_path, blank=True, null=True)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

class Report(models.Model):
  id = models.AutoField(primary_key=True)
  review = models.ForeignKey(Review, on_delete=models.CASCADE)
  report_title = models.CharField(max_length=50)
  report_reason = models.CharField(max_length=50)
  created_at = models.DateTimeField(auto_now_add=True)
