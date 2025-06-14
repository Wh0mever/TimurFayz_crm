from django.contrib import admin

from students.models import StudyGroup, StudyLesson, StudentToGroup, Student, StudyGroupDay, StudentTransaction, \
    StudentBonus


class StudentToGroupInline(admin.TabularInline):
    model = StudentToGroup
    extra = 0


class StudyLessonInline(admin.TabularInline):
    model = StudyLesson
    extra = 0


class StudyGroupDayInline(admin.TabularInline):
    model = StudyGroupDay
    extra = 0


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'start_date', 'end_date']
    list_display_links = ['id', 'name']
    inlines = [StudyGroupDayInline, StudyLessonInline, StudentToGroupInline]


@admin.register(StudyLesson)
class StudyLessonAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'date']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'gender', 'phone_number', 'is_active']
    list_display_links = ['id', 'full_name']
    inlines = [StudentToGroupInline]


@admin.register(StudentTransaction)
class StudentTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'student', 'transaction_date']
    list_display_link = ['id', 'group', 'student']
    list_filter = ['group', 'student']


@admin.register(StudentBonus)
class StudentBonusAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'created_at', 'amount']