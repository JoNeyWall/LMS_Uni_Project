# The purpose of validate.py is to check various user inputs and report any errors.
from . import models

def get_grade_errors(grade, submission_id, assignment_id):
    #return at the end
    errors = []

    #Attempt float parse
    try:
        grade = float(grade)
        #Check bounds
        if grade > 100 or grade < 0:
            errors.append(f"Error: Grade = {grade}, is outside the range 0 to 100.")
    except:
        errors.append(f"Error: Grade = {grade}, contains non-numbers")
    
    try:
        submission = models.Submission.objects.get(id=submission_id)
        if (submission.assignment.id != assignment_id):
            errors.append("Error: Attempting to assign score to the incorrect assignment.")
    except:
        errors.append(f"Error: attempting to retrieve a sumbission that does not exist.")

    return errors