from datetime import datetime, timedelta, date
from typing import Iterable

from dateutil.relativedelta import relativedelta
from django.db import IntegrityError, transaction
from django.db.models import F, Sum, Case, When, Value, DateField, DecimalField, DateTimeField, BooleanField, TextField
from django.db.models.functions import Abs, Cast

from students.exception import StudyGroupDayAlreadyExists, StudentAlreadyVisitedLesson, StudentNotFromThisGroup
from students.helpers import get_diff_month
from students.models import StudyGroup, StudyLesson, StudentToGroup, StudyGroupDay, Student, StudentVisit, \
    StudentTransaction, StudentBonus


def increase_student_balance(student_id, amount):
    Student.objects.filter(id=student_id).update(balance=F('balance') + amount)


def decrease_student_balance(student_id, amount):
    Student.objects.filter(id=student_id).update(balance=F('balance') - amount)


def generate_student_account_number():
    last_student = Student.objects.filter(account_number__isnull=False) \
        .order_by('-account_number').values('account_number').first()
    last_number = last_student['account_number'] + 1 if last_student else 1000000
    return last_number


def min_days_between_weekdays(day1, day2):
    # Forward difference
    forward_diff = (day2 - day1) % 7
    # Backward difference
    backward_diff = (day1 - day2) % 7
    return min(forward_diff, backward_diff)


def calculate_days_until_weekday(start_weekday, target_weekday):
    return (target_weekday - start_weekday + 7) % 7 or 7


def find_next_study_weekday(current_day, target_days):
    day_differences = [
        (day - current_day + 7) % 7 or 7 for day in target_days
    ]
    return target_days[day_differences.index(min(day_differences))]


def calculate_days_shift_between_weekdays(current_weekday, new_day_of_week):
    forward_diff = (new_day_of_week - current_weekday) % 7
    backward_diff = (current_weekday - new_day_of_week) % 7
    return forward_diff if forward_diff < backward_diff else -backward_diff


def create_study_days_for_group(group: StudyGroup, study_days_list: list):
    try:
        for study_day in study_days_list:
            StudyGroupDay.objects.create(
                group=group,
                day_of_week=study_day['day_of_week'],
                start_time=study_day['start_time'],
            )
    except IntegrityError as e:
        raise StudyGroupDayAlreadyExists


def create_group_lessons(group: StudyGroup):
    start_date = group.start_date
    end_date = group.end_date
    study_days = {item.day_of_week: item.start_time for item in group.study_days.all()}
    lesson_weekdays = sorted(study_days.keys())

    current_date: date = start_date.date()
    lessons_to_create = []
    while current_date <= end_date.date():
        current_weekday = current_date.weekday() + 1
        if current_weekday in lesson_weekdays:
            lesson_date = datetime.combine(current_date, study_days[current_weekday])
            lessons_to_create.append(StudyLesson(group=group, date=lesson_date))

        next_lesson_weekday = find_next_study_weekday(current_weekday, lesson_weekdays)
        days_to_next_weekday = calculate_days_until_weekday(current_weekday, next_lesson_weekday)
        current_date += timedelta(days=days_to_next_weekday)

    StudyLesson.objects.bulk_create(lessons_to_create)


def create_group_lessons_by_study_day(group: StudyGroup, study_day: StudyGroupDay):
    end_date: date = group.end_date.date()
    current_date: date = max(group.start_date.date(), datetime.today())
    lessons_to_create = []
    while current_date <= end_date:
        current_weekday = current_date.weekday() + 1
        if current_weekday == study_day.day_of_week:
            lesson_date = datetime.combine(current_date, study_day.start_time)
            lessons_to_create.append(StudyLesson(group=group, date=lesson_date))
            current_date += timedelta(days=7)
        else:
            days_to_next_weekday = calculate_days_until_weekday(current_weekday, study_day.day_of_week)
            current_date += timedelta(days=days_to_next_weekday)

    StudyLesson.objects.bulk_create(lessons_to_create)


def delete_group_lessons_by_study_date(study_day: StudyGroupDay):
    group = study_day.group
    today = datetime.today()
    with transaction.atomic():
        group.lessons.filter(date__iso_week_day=study_day.day_of_week, date__gte=today).delete()
        study_day.delete()


def update_study_day(study_day: StudyGroupDay, new_start_time=None, new_day_of_week=None):
    group = study_day.group
    today = datetime.today()

    if new_start_time and new_start_time != study_day.start_time:
        group.lessons.filter(date__gte=today).update(start_time=new_start_time)
        study_day.start_time = new_start_time

    if new_day_of_week and new_day_of_week != study_day.day_of_week:
        process_day_of_week_change(study_day, new_day_of_week)
        study_day.day_of_week = new_day_of_week
    study_day.save(update_fields=['start_time', 'day_of_week'])
    return study_day


def process_day_of_week_change(study_day: StudyGroupDay, new_day_of_week):
    today = datetime.today()
    group = study_day.group
    current_weekday = study_day.day_of_week
    lessons = StudyLesson.objects.filter(
        date__iso_week_day=study_day.day_of_week,
        date__gte=today
    ).order_by('date')

    if lessons.exists():
        first_lesson = lessons.first()
        days_shift = calculate_days_shift_between_weekdays(current_weekday, new_day_of_week)

        if first_lesson.date - timedelta(days=days_shift) < today:
            days_shift += 7

        lessons.update(date=F('date') + timedelta(days=days_shift))

        last_lesson = lessons.last()
        if last_lesson.date() > group.end_date:
            group.end_date = last_lesson.date()
            group.save(update_fields=['end_date'])


def add_student_transactions_by_groups(student: Student, groups):
    today = datetime.today()
    transactions = []
    transactions_sum = 0
    for group in groups:
        student_to_group = student.groups.filter(group=group, student=student).first()
        months_passed = get_diff_month(student_to_group.joined_date, today)
        transaction_date = student_to_group.joined_date.replace(day=1)
        for i in range(0, months_passed + 1):
            t_obj = StudentTransaction(
                group=group,
                student=student,
                transaction_date=transaction_date,
                amount=group.price
            )
            transactions.append(t_obj)
            transactions_sum += group.price
            transaction_date += relativedelta(months=1)

    StudentTransaction.objects.bulk_create(transactions)
    decrease_student_balance(student.id, transactions_sum)
    student.refresh_from_db(fields=['balance'])


def remove_student_transactions_by_groups(student: Student, group_ids):
    transactions = StudentTransaction.objects.filter(student=student, group_id__in=group_ids)
    transactions_sum = transactions.aggregate(amount_sum=Sum('amount', default=0))['amount_sum']

    with transaction.atomic():
        transactions.delete()
        increase_student_balance(student.id, transactions_sum)
        student.refresh_from_db(fields=['balance'])


def add_students_to_group(group: StudyGroup, student_ids: Iterable, joined_date=None):
    if student_ids:
        joined_date = group.start_date if not joined_date else joined_date
        students = Student.objects.filter(id__in=student_ids)
        StudentToGroup.objects.bulk_create(
            [StudentToGroup(group=group, student_id=student_id, joined_date=joined_date) for student_id in student_ids]
        )

        for student in students:
            add_student_transactions_by_groups(student, [group])
        # StudentTransaction.objects.bulk_create(
        #     [
        #         StudentTransaction(
        #             group=group,
        #             student_id=student_id,
        #             transaction_date=datetime.today(),
        #             amount=group.price
        #         ) for student_id in student_ids
        #     ]
        # )
        # Student.objects.filter(id__in=student_ids).update(balance=F('balance') - group.price)


def remove_students_from_group(group: StudyGroup, student_ids: Iterable):
    if student_ids:
        students = Student.objects.filter(id__in=student_ids)
        StudentToGroup.objects.filter(group=group, student_id__in=student_ids).delete()

        # for student in students:
        #     remove_student_transactions_by_groups(student, [group.id])
        # StudentTransaction.objects.filter(group=group, student_id__in=student_ids).delete()
        # Student.objects.filter(id__in=student_ids).update(balance=F('balance') + group.price)


def update_group_students_list(group: StudyGroup, students_ids: list, joined_date):
    if students_ids is not None:
        current_students_ids = set(group.students.values_list('student_id', flat=True))
        new_students_ids = set(students_ids) - current_students_ids
        removed_students_ids = current_students_ids - set(students_ids)

        if new_students_ids:
            add_students_to_group(group, new_students_ids, joined_date)
        remove_students_from_group(group, removed_students_ids)


def add_student_to_groups(student: Student, group_ids: Iterable, joined_date: datetime):
    if group_ids:
        with transaction.atomic():
            groups = StudyGroup.objects.filter(id__in=group_ids)
            StudentToGroup.objects.bulk_create(
                [StudentToGroup(
                    student=student,
                    group_id=group.id,
                    joined_date=joined_date if joined_date else group.start_date
                ) for group in groups]
            )

            add_student_transactions_by_groups(student, groups)


def remove_student_from_groups(student: Student, group_ids: Iterable):
    if group_ids:
        StudentToGroup.objects.filter(student=student, group_id__in=group_ids).delete()
        # remove_student_transactions_by_groups(student, group_ids)


def update_student_groups_list(student, group_ids: list):
    if group_ids is not None:
        current_group_ids = set(student.groups.values_list('group_id', flat=True))
        new_group_ids = set(group_ids) - current_group_ids
        removed_group_ids = current_group_ids - set(group_ids)

        add_student_to_groups(student, new_group_ids)
        remove_student_from_groups(student, removed_group_ids)


def recalculate_group_transactions(group: StudyGroup):
    today = datetime.today()
    students = Student.objects.filter(groups__in=group.students.all())

    months_passed = get_diff_month(group.start_date, today)
    transaction_dates = [
        group.start_date.replace(day=1) + relativedelta(months=i)
        for i in range(months_passed + 1)
    ]

    existing_transactions = StudentTransaction.objects.filter(group=group)
    existing_dates_map = {
        (tx.student_id, tx.transaction_date): tx
        for tx in existing_transactions
    }

    transactions_to_create = []
    for student in students:
        for transaction_date in transaction_dates:
            if (student.id, transaction_date) not in existing_dates_map:
                transactions_to_create.append(
                    StudentTransaction(
                        group=group,
                        student=student,
                        transaction_date=transaction_date,
                        amount=group.price
                    )
                )
                student.balance -= group.price

    deleted_transactions = existing_transactions.filter(
        transaction_date__gt=group.end_date,
        transaction_date__lt=group.start_date,
    )
    for tx in deleted_transactions:
        tx.student.balance += tx.amount
    deleted_transactions.delete()

    StudentTransaction.objects.bulk_create(transactions_to_create)
    Student.objects.bulk_update(students, fields=['balance'])


def create_student_bonus(student: Student, amount, comment, user):
    with transaction.atomic():
        student_bonus = StudentBonus.objects.create(
            student=student,
            amount=amount,
            comment=comment,
            created_user=user,
        )
        increase_student_balance(student.id, amount)
        student.refresh_from_db(fields=['balance'])

    return student_bonus


def handle_student_bonus_delete(student_bonus: StudentBonus):
    decrease_student_balance(student_bonus.student.id, student_bonus.amount)


def create_student_visit(lesson: StudyLesson, student: Student):
    with transaction.atomic():
        if StudentVisit.objects.filter(lesson=lesson, student=student).exists():
            raise StudentAlreadyVisitedLesson
        if lesson.group.id not in student.groups.values_list('group_id', flat=True):
            raise StudentNotFromThisGroup
        visit_obj = StudentVisit.objects.create(lesson=lesson, student=student)
        increase_student_balance(student.pk, lesson.group.lesson_price)
    return visit_obj


def delete_student_visit(visit: StudentVisit):
    visit.delete()
    decrease_student_balance(visit.student.pk, visit.lesson.group.lesson_price)


def get_student_debit_credit_report(student: Student):
    payments = student.payments.filter(
        is_deleted=False,
    ).annotate(
        date=Cast(F('payment_date'), output_field=DateTimeField()),
        balance_change_type=F('payment_type'),
        reason=Value("PAYMENT"),
        mark_for_delete=F('marked_for_delete'),
        total=Cast(F('amount'), DecimalField(max_digits=15, decimal_places=2)),
        comment_text=F('comment'),
    ).values('id', 'date', 'balance_change_type', 'reason', 'total', 'mark_for_delete', 'comment_text')
    transactions = student.transactions.filter().annotate(
        date=Cast(F('transaction_date'), output_field=DateTimeField()),
        balance_change_type=Value("OUTCOME"),
        reason=Value("STUDY"),
        mark_for_delete=Value(False, output_field=BooleanField(default=False)),
        total=Cast(F('amount'), DecimalField(max_digits=15, decimal_places=2)),
        comment_text=Value("", output_field=TextField())
    ).values('id', 'date', 'balance_change_type', 'reason', 'total', 'mark_for_delete', 'comment_text')
    bonuses = student.bonuses.filter(is_deleted=False).annotate(
        date=Cast(F('created_at'), output_field=DateTimeField()),
        balance_change_type=Value("INCOME"),
        reason=Value("BONUS"),
        mark_for_delete=F('marked_for_delete'),
        total=Cast(F('amount'), DecimalField(max_digits=15, decimal_places=2)),
        comment_text=F('comment'),
    ).values('id', 'date', 'balance_change_type', 'reason', 'total', 'mark_for_delete', 'comment_text')
    balance_adjustments = student.balance_adjustments.annotate(
        date=Cast(F('created_at'), output_field=DateTimeField()),
        balance_change_type=Case(
            When(new_balance__gte=F('old_balance'), then=Value("INCOME")),
            default=Value("OUTCOME")
        ),
        mark_for_delete=F('marked_for_delete'),
        total=Abs(F('new_balance') - F('old_balance'), output_field=DecimalField(max_digits=15, decimal_places=2)),
        reason=Value("ADJUSTMENT"),
        comment_text=F('comment'),
    ).values('id', 'date', 'balance_change_type', 'reason', 'total', 'mark_for_delete', 'comment_text')

    balance_changes = payments.union(transactions, bonuses, balance_adjustments).order_by('date')

    balance = 0
    for item in balance_changes:
        item['balance_before'] = balance
        amount = item['total'] if item['balance_change_type'] == "INCOME" else -item['total']
        balance += amount
        item['balance_after'] = balance

    return balance_changes
