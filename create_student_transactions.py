import datetime
import os
import django
from django.db import transaction
from django.db.models import F

from dotenv import load_dotenv


load_dotenv()

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "timur_fayz_backend.settings"
)
django.setup()

from students.models import StudyGroup, Student, StudentTransaction

def create_transactions():
    today = datetime.datetime.now().date()
    groups = StudyGroup.objects.get_available().filter(
        start_date__lte=today,
        end_date__gte=today
    )
    print(groups)
    with transaction.atomic():
        for group in groups:
            students = Student.objects.get_available().filter(groups__group=group).distinct()
            print(students)
            StudentTransaction.objects.bulk_create(
                StudentTransaction(
                    student=student,
                    group=group,
                    amount=group.price,
                    transaction_date=today,
                ) for student in students
            )
            students.update(balance=F('balance') - group.price)


if __name__ == '__main__':
    create_transactions()
