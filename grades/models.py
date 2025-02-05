from django.db import models
from django.contrib.auth.models import User, Group
from . import helper
from django.core.exceptions import PermissionDenied

# Create your models here.

#Assignment object
class Assignment(models.Model):
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    deadline = models.DateTimeField(blank=True, null=True)
    weight = models.IntegerField()
    points = models.IntegerField()

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    author = models.ForeignKey(User(), on_delete=models.CASCADE)
    grader = models.ForeignKey(User(), on_delete=models.SET_NULL, related_name='graded_set', null=True)
    file = models.FileField()
    score = models.FloatField(blank=True, null=True)

    def change_grade(self, user, grade):
        if user.is_superuser or user == self.grader:
            self.score = grade
        else:
            raise PermissionDenied
        
    def view_submission(self, user):
        if not (user == self.author or user == self.grader or user.is_superuser):
            raise PermissionDenied