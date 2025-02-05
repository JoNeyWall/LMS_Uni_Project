from django.shortcuts import HttpResponse, redirect, render, Http404
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from . import models
from . import validate
from . import helper

# Create your views here.
@login_required
def index(request):
    all_assignments = models.Assignment.objects.all()
    return render(request, "index.html", {"all_assignments":all_assignments})

@login_required
def assignment(request, assignment_id):
    error = ''
    if request.method == "POST":
        file = request.FILES.get("file", None)
        if file:
            if file.size > 64 * 1024 * 1024:
                error = 'Files cannot be greater than 64MB.'
            elif not str(file.name).endswith('.pdf'):
                error = 'You can only submit .pdf files'
            elif not next(file.chunks()).startswith(b'%PDF-'):
                error = 'The pdf file you submitted is not formatted correctly.'

    if request.method == "POST" and error == '':
        assignment = models.Assignment.objects.get(id=assignment_id)
        file = request.FILES.get("file", None)
        
        submission, new_submission = models.Submission.objects.get_or_create(
            assignment=assignment,
            author=request.user,
            defaults={
                "grader": helper.pick_grader(assignment), 
                "file": file
                }
        )

        if not new_submission and file:
            submission.file = file
            submission.save()

        return redirect(f"/{assignment_id}/")

    #Beginning of get request
    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
    except models.Assignment.DoesNotExist:
        raise Http404("Invalid Assignment ID")
    
    student_total = models.Group.objects.get(name="Students").user_set.count()
    
    #Determine the type of user
    user = request.user
    is_student = helper.is_student(user) or not user.is_authenticated
    is_ta = helper.is_ta(user) or user.is_superuser

    #What to show
    if is_ta:
        if user.is_superuser:
            assigned_total = models.Submission.objects.filter(assignment=assignment).count()
        else:
            assigned_total = models.Submission.objects.filter(assignment=assignment, grader=user).count()
        submission_total = models.Submission.objects.filter(assignment=assignment).count()
    else:
        assigned_total = None
        submission_total = None

    if user.is_authenticated:
        submission = models.Submission.objects.filter(assignment=assignment, author=user).last()
    else:
        submission = None

    #Submission grade information
    submitted = (submission is not None and submission.file is not None)
    graded = (submission is not None and submission.score is not None and submission.score is not '')
    past_due = helper.is_past_due(assignment)
    grade_info = ''

    file_anchor = ''
    if submitted:
        file_anchor = '<a href="/uploads/' + str(submission.file) + '">' + str(submission.file.name) + '</a>'

    if submitted and graded:
        grade_info = 'Your submission, ' + file_anchor + ', received ' + str(int(submission.score)) + '/' + str(assignment.weight) + ' points (' + str(round((submission.score/assignment.weight) * 100)) + '%)'
    elif submitted and not graded and past_due:
        grade_info = 'Your submission, ' + file_anchor + ', is being graded.'
    elif submitted and not past_due:
        grade_info = 'Your current submission is ' + file_anchor
    elif not submitted and not past_due:
        grade_info = 'No current submission.'
    elif not submitted and past_due:
        grade_info = 'You did not submit this assignment and received 0 points.'

    return render(request, "assignment.html", {
        "assignment":assignment,
        "submission":submission,
        "student_total":student_total,
        "submission_total":submission_total,
        "assigned_total":assigned_total,
        "is_student":is_student,
        "is_ta":is_ta,
        "grade_info":grade_info,
        "past_due":past_due,
        "error":error
    })

@login_required
def submissions(request, assignment_id):
    user = request.user
    is_ta = helper.is_ta(user) or user.is_superuser
    if not is_ta:
        raise PermissionDenied

    errors = {}
    if request.method == "POST":
        grades = helper.get_grades(request)
        for submission_id in grades:
            errors[submission_id] = validate.get_grade_errors(grades[submission_id], submission_id, assignment_id)
            if not errors[submission_id]:
                submission = models.Submission.objects.get(id=submission_id)
                submission.change_grade(user, grades[submission_id])
                submission.save()
        if not errors:
            return redirect(f"/{assignment_id}/submissions")

    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
    except models.Assignment.DoesNotExist:
        raise Http404("Invalid Assignment ID")
    
    user = request.user
    is_ta = helper.is_ta(user) or user.is_superuser

    if not is_ta:
        raise PermissionDenied

    #which submissions should be available
    submissions = []
    if is_ta:
        if user.is_superuser:
            submissions = models.Submission.objects.filter(assignment=assignment).order_by('author')
        else:
            submissions = models.Submission.objects.filter(assignment=assignment, grader=user).order_by('author')

    return render(request, "submissions.html", {
        "is_ta":is_ta,
        "submissions":submissions,
        "assignment":assignment,
        "errors":errors
    })

@login_required
def show_upload(request, filename):
    user = request.user
    submission = models.Submission.objects.get(file=filename)
    submission.view_submission(user)

    if not str(submission.file.name).endswith('.pdf'):
        raise Http404("Invalid PDF")
    elif not next(submission.file.chunks()).startswith(b'%PDF-'):
        raise Http404("Invalid PDF")

    response = HttpResponse(submission.file)
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = f'attachment; filename="{submission.file.name}"'
    return response

@login_required
def profile(request):
    all_assignments = models.Assignment.objects.all()
    user = request.user
    is_ta = helper.is_ta(user) or user.is_superuser

    assigned_titles = []
    assigned_graded = []
    assigned = []
    assigned_ids = []
    weights = []
    scores = []
    final_score = 0
    total_score_weight = 0

    if is_ta:
        for assignment in all_assignments:
            assigned_titles.append(assignment.title)
            if user.is_superuser:
                assigned_graded.append(models.Submission.objects.filter(assignment=assignment, score__isnull=False).count())
                assigned.append(models.Submission.objects.filter(assignment=assignment).count())
            else:
                assigned_graded.append(models.Submission.objects.filter(assignment=assignment, grader=user, score__isnull=False).count())
                assigned.append(models.Submission.objects.filter(assignment=assignment, grader=user).count())
            assigned_ids.append(assignment.id)
            scores.append(None)
            weights.append(None)
    else:
        for assignment in all_assignments:
            assigned_titles.append(assignment.title)
            assigned_graded.append(None)
            assigned.append(None)
            assigned_ids.append(assignment.id)
            weights.append(assignment.weight)

            if user.is_authenticated:
                submission = models.Submission.objects.filter(assignment=assignment, author=user).last()
            else:
                submission = None

            #State of a grade calculation
            if not helper.is_past_due(assignment):
                scores.append('Not Due')
            else:
                if submission and submission.file:
                    if submission.score == '' or submission.score is None:
                        scores.append('Ungraded')
                    else:
                        #Score should always be between 100% and 0%
                        scores.append(str((submission.score / assignment.weight) * 100) + '%')
                        final_score += submission.score
                        total_score_weight += assignment.weight
                else:
                    scores.append('Missing')
                    final_score += 0
                    total_score_weight += assignment.weight
            
        if total_score_weight == 0:
            final_score = '100%'
        else:
            final_score = str(round((final_score / total_score_weight) * 100, 1)) + '%'
                    

    zipped_data = zip(assigned_titles, assigned_graded, assigned, assigned_ids, scores, weights)

    return render(request, "profile.html", {
        "zipped_data":zipped_data,
        "user":user,
        "is_ta":is_ta,
        "final_score":final_score
    })

def login_form(request):
    if request.method == "POST":
        username = request.POST.get("username_input", "")
        password = request.POST.get("password_input", "")
        next = request.POST.get("next", "/profile/")

        if not url_has_allowed_host_and_scheme(next, None):
            next = '/profile/'

        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next)
        else:
            error = 'Username and password did not match.'
            return render(request, "login.html", {
                "next":next,
                "error":error
            })

    next = request.GET.get("next", "/profile/")
    return render(request, "login.html", {
        "next":next
    })
        
def logout_form(request):
    logout(request)
    return redirect("/profile/login")
