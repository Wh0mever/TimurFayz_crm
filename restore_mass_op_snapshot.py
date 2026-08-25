# -*- coding: utf-8 -*-
"""Восстановление состояния студентов из бэкапа массовой операции.

Каждая массовая операция (перенос/удаление/восстановление) перед выполнением
пишет снимок затронутых записей в backups/mass_operations/*.json.gz.
Этот скрипт возвращает затронутых студентов ровно в состояние ДО операции:
сами студенты (включая баланс и флаги), их привязки к группам и транзакции.

Запуск (из каталога бэкенда):
    venv/bin/python restore_mass_op_snapshot.py backups/mass_operations/<файл>.json.gz

Скрипт трогает ТОЛЬКО студентов из снимка. Всё в одной транзакции.
"""
import gzip
import json
import os
import sys

import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timur_fayz_backend.settings')
django.setup()

from django.core import serializers as dj_serializers
from django.db import transaction

from students.models import StudentToGroup, StudentTransaction


def main():
    if len(sys.argv) != 2:
        print('Использование: python restore_mass_op_snapshot.py <файл .json.gz>')
        sys.exit(1)

    path = sys.argv[1]
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        snapshot = json.load(f)

    ids = snapshot['student_ids']
    print('Снимок: %s от %s, операция: %s' % (
        snapshot['tag'], snapshot['created_at'], snapshot.get('operation') or '—'))
    print('Затронуто студентов: %d' % len(ids))

    answer = input('Восстановить их состояние на момент снимка? [yes/no]: ')
    if answer.strip().lower() not in ('yes', 'y', 'да'):
        print('Отменено.')
        sys.exit(0)

    restored = 0
    with transaction.atomic():
        # Текущие привязки и транзакции затронутых студентов заменяются
        # содержимым снимка целиком (PK сохраняются из снимка).
        StudentToGroup.objects.filter(student_id__in=ids).delete()
        StudentTransaction.objects.filter(student_id__in=ids).delete()
        for section in ('students', 'student_to_group', 'transactions'):
            for obj in dj_serializers.deserialize('json', snapshot[section]):
                obj.save()
                restored += 1

    print('Готово: восстановлено объектов: %d' % restored)


if __name__ == '__main__':
    main()
