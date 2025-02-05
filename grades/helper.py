#This helper class is to store any helpers that may be needed
from django.db import models
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.models import Group

#Returns dictionary of grades with submission_id as key and grade as value.
def get_grades(request):
    grades = {}
    for key in request.POST:
        if "grade-" not in key:
            continue
        else:
            submission_id = int(key.removeprefix("grade-"))
            grade = request.POST[key]
            grades[submission_id] = grade
    return grades

#Student Check
def is_student(user):
    return user.groups.filter(name="Students").exists()

def is_ta(user):
    return user.groups.filter(name="Teaching Assistants").exists()

#determine if something is past due at submission time, not past due if there is no due date
def is_past_due(assignment):
    if assignment.deadline:
        return assignment.deadline < timezone.now()
    return False

#return ta with the fewest assignments to grade
def pick_grader(assignment):
    tas = Group.objects.get(name="Teaching Assistants")
    chosen_ta = (tas.user_set.annotate(total_assigned=Count('graded_set', filter=models.Q(graded_set__assignment=assignment))).order_by('total_assigned').first())
    return chosen_ta
