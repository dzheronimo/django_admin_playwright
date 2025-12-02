from django.db import models


class SiteInfo(models.Model):
    site_name = models.CharField(max_length=100)
    site_url = models.URLField()
