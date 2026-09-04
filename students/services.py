import gzip
import json
import os
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Iterable

from dateutil.relativedelta import relativedelta
from django.db import IntegrityError, transaction
from django.db.models import F, Sum, Case, When, Value, DateField, DecimalField, DateTimeField, BooleanField, TextField
from django.db.models.functions import Abs, Cast
from django.conf import settings
from django.core import serializers as dj_serializers
from django.utils import timezone

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


def transfer_student_to_group(student: Student, group_from: StudyGroup, group_to: StudyGroup, joined_date: datetime):
    with transaction.atomic():
        remove_student_from_groups(student, [group_from.id])
        transactions = StudentTransaction.objects.filter(
            student=student,
            group_id=group_from.id,
            transaction_date__gte=joined_date.replace(day=1),
        )
        transactions_sum = transactions.aggregate(amount_sum=Sum('amount', default=0))['amount_sum']

        transactions.delete()
        increase_student_balance(student.id, transactions_sum)
        student.refresh_from_db(fields=['balance'])

        add_student_to_groups(student, [group_to.id], joined_date)


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


def _transfer_refund_sum(student: Student, group_from: StudyGroup, joined_date: date):
    """Сумма списаний старой группы, которые вернёт transfer_student_to_group.

    Повторяет фильтр из transfer_student_to_group один в один — используется
    для dry-run предпросмотра и отчёта, сама денег не трогает.
    """
    return StudentTransaction.objects.filter(
        student=student,
        group_id=group_from.id,
        transaction_date__gte=joined_date.replace(day=1),
    ).aggregate(amount_sum=Sum('amount', default=0))['amount_sum']


class MassOperationBackupError(Exception):
    """Бэкап перед массовой операцией не создан — операция должна быть отменена."""


def create_mass_operation_snapshot(tag: str, student_ids: Iterable, operation_params: dict = None) -> str:
    """Файловый бэкап затронутых записей ПЕРЕД массовой операцией.

    Требование клиента: возможность бэкапа в любых случаях. Пишет gzip-JSON
    с полным состоянием студентов, их привязок к группам и транзакций
    (django-сериализация — восстанавливается с исходными PK).
    Восстановление: python restore_mass_op_snapshot.py <файл>.
    Любая ошибка записи -> MassOperationBackupError, операция НЕ выполняется.
    """
    try:
        ids = sorted(set(int(i) for i in student_ids))
        payload = {
            'tag': tag,
            'created_at': datetime.now().isoformat(),
            'operation': operation_params or {},
            'student_ids': ids,
            'students': dj_serializers.serialize('json', Student.objects.filter(id__in=ids)),
            'student_to_group': dj_serializers.serialize('json', StudentToGroup.objects.filter(student_id__in=ids)),
            'transactions': dj_serializers.serialize('json', StudentTransaction.objects.filter(student_id__in=ids)),
        }
        backup_dir = os.path.join(settings.BASE_DIR, 'backups', 'mass_operations')
        os.makedirs(backup_dir, exist_ok=True)
        filename = '%s_%s.json.gz' % (datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), tag)
        path = os.path.join(backup_dir, filename)
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
        # контрольное чтение: бэкап обязан быть валидным
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            json.load(f)
        return path
    except Exception as e:
        raise MassOperationBackupError(str(e))


def mass_transfer_students(group_from: StudyGroup, student_ids: Iterable, joined_date: date,
                           group_to: StudyGroup = None, dry_run: bool = False, new_group: dict = None):
    """Массовый перенос студентов между группами (перевод на следующий класс).

    Оркестрация боевого transfer_student_to_group: никакой новой денежной логики.
    - переносятся только активные студенты, реально привязанные к group_from;
    - уже привязанные к group_to пропускаются (дедуп — unique-констрейнта в БД нет,
      двойная привязка означала бы двойное списание кроном);
    - dry_run=True считает те же суммы (возврат старой группы + до-начисление новой),
      ничего не записывая;
    - применение — в одной транзакции: упало на любом студенте → откатилось всё,
      повторный запуск того же запроса — no-op по уже перенесённым.
    """
    if (group_to is None) == (new_group is None):
        raise ValueError('Нужно указать либо group_to, либо new_group')

    # Целевая группа: существующая или новая (создаётся при применении —
    # клон отдела/преподавателя/расписания текущей группы, свои даты и цена).
    target_price = group_to.price if group_to else Decimal(str(new_group['price']))
    target_name = group_to.name if group_to else new_group['name']
    new_group_meta = {k: str(v) for k, v in new_group.items()} if new_group else None

    today = datetime.today()
    months_passed = get_diff_month(joined_date, today)
    back_months = months_passed + 1 if months_passed >= 0 else 0

    requested_ids = set(student_ids)
    eligible = list(
        Student.objects.get_available()
        .filter(id__in=requested_ids, groups__group=group_from)
        .distinct()
    )
    eligible_ids = {s.id for s in eligible}

    already_in_target = set(
        StudentToGroup.objects.filter(group=group_to, student_id__in=eligible_ids)
        .values_list('student_id', flat=True)
    ) if group_to else set()

    skipped = []
    missing_ids = requested_ids - eligible_ids
    if missing_ids:
        missing_names = dict(Student.objects.filter(id__in=missing_ids).values_list('id', 'full_name'))
        for student_id in sorted(missing_ids):
            skipped.append({
                'student_id': student_id,
                'full_name': missing_names.get(student_id, f'ID {student_id}'),
                'reason': 'Не найден среди активных студентов группы-источника',
            })

    to_transfer = []
    for student in eligible:
        if student.id in already_in_target:
            skipped.append({
                'student_id': student.id,
                'full_name': student.full_name,
                'reason': 'Уже состоит в целевой группе',
            })
        else:
            to_transfer.append(student)

    rows = []
    if dry_run:
        for student in to_transfer:
            refund = _transfer_refund_sum(student, group_from, joined_date)
            charge = target_price * back_months
            rows.append({
                'student_id': student.id,
                'full_name': student.full_name,
                'balance_before': str(student.balance),
                'refund': str(refund),
                'charge': str(charge),
                'balance_after': str(student.balance + refund - charge),
            })
    else:
        backup_path = create_mass_operation_snapshot(
            'mass_transfer',
            [student.id for student in to_transfer],
            {
                'group_from': group_from.id,
                'group_to': group_to.id if group_to else None,
                'new_group': new_group_meta,
                'joined_date': joined_date.isoformat(),
            },
        )
        with transaction.atomic():
            if new_group:
                group_to = StudyGroup.objects.create(
                    name=new_group['name'],
                    start_date=new_group['start_date'],
                    end_date=new_group['end_date'],
                    price=new_group['price'],
                    department=group_from.department,
                    teacher=group_from.teacher,
                )
                # расписание (дни/время) переносим как есть, уроки/визиты — нет
                StudyGroupDay.objects.bulk_create([
                    StudyGroupDay(group=group_to, day_of_week=d.day_of_week, start_time=d.start_time)
                    for d in group_from.study_days.all()
                ])
            for student in to_transfer:
                balance_before = student.balance
                refund = _transfer_refund_sum(student, group_from, joined_date)
                transfer_student_to_group(
                    student=student,
                    group_from=group_from,
                    group_to=group_to,
                    joined_date=joined_date,
                )
                student.refresh_from_db(fields=['balance'])
                rows.append({
                    'student_id': student.id,
                    'full_name': student.full_name,
                    'balance_before': str(balance_before),
                    'refund': str(refund),
                    'charge': str(group_to.price * back_months),
                    'balance_after': str(student.balance),
                })

    warnings = []
    if target_price == 0:
        warnings.append(
            'Цена целевой группы — 0 сум: ежемесячные списания будут нулевыми. '
            'Проверьте цену группы до 1-го числа.'
        )
    if back_months > 0 and to_transfer:
        warnings.append(
            f'Дата зачисления в прошлом: каждому студенту будет до-начислено '
            f'{back_months} мес. × {target_price} сум по новой группе.'
        )
    total_refund = sum(Decimal(r['refund']) for r in rows) if rows else Decimal(0)
    if total_refund > 0:
        warnings.append(
            'Студентам будут возвращены списания старой группы начиная с месяца даты зачисления '
            f'(всего {total_refund} сум).'
        )

    return {
        'dry_run': dry_run,
        'group_from': {'id': group_from.id, 'name': group_from.name},
        'group_to': {'id': group_to.id if group_to else None, 'name': target_name, 'price': str(target_price)},
        'new_group_created': bool(new_group) and not dry_run,
        'joined_date': joined_date.isoformat(),
        'students': rows,
        'skipped': skipped,
        'backup_file': os.path.basename(backup_path) if not dry_run and to_transfer else None,
        'totals': {
            'count': len(rows),
            'skipped_count': len(skipped),
            'refund_sum': str(total_refund),
            'charge_sum': str(sum(Decimal(r['charge']) for r in rows) if rows else Decimal(0)),
        },
        'warnings': warnings,
    }


def mass_delete_students(student_ids: Iterable, user):
    """Массовое мягкое удаление студентов.

    Отличие от одиночного destroy: account_number НЕ обнуляется — это позволяет
    «Отмене» (mass_restore_students) вернуть студента ровно в исходное состояние.
    Номера генерируются как max+1 (generate_student_account_number), поэтому
    сохранённый номер удалённого студента конфликтов не создаёт.
    """
    students = Student.objects.get_available().filter(id__in=set(student_ids))
    deleted = list(students.values('id', 'full_name'))
    backup_path = create_mass_operation_snapshot(
        'mass_delete', [d['id'] for d in deleted],
    ) if deleted else None
    with transaction.atomic():
        students.update(
            is_deleted=True,
            is_active=False,
            deleted_user=user,
            deleted_at=timezone.now(),
        )
    return deleted, (os.path.basename(backup_path) if backup_path else None)


def mass_restore_students(student_ids: Iterable):
    """Отмена массового удаления: возвращает мягко удалённых студентов."""
    students = Student.objects.filter(id__in=set(student_ids), is_deleted=True)
    restored = list(students.values('id', 'full_name'))
    backup_path = create_mass_operation_snapshot(
        'mass_restore', [r['id'] for r in restored],
    ) if restored else None
    with transaction.atomic():
        students.update(
            is_deleted=False,
            is_active=True,
            deleted_user=None,
            deleted_at=None,
        )
    return restored, (os.path.basename(backup_path) if backup_path else None)
