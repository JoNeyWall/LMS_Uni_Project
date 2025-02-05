from django.contrib import admin
from .models import Assignment
from .models import Submission

# Register your models here.
admin.site.register(Assignment)
admin.site.register(Submission)