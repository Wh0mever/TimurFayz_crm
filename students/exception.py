from base.exceptions import BusinessLogicException


class StudyGroupDayAlreadyExists(BusinessLogicException):
    default_detail = "Расписание на этот день недели уже добавлено"
    default_code = "study_group_day_already_exists"


class StudentAlreadyVisitedLesson(BusinessLogicException):
    default_detail = "Студент уже посетил данное занятие"
    default_code = "student_already_visited_lesson"


class StudentNotFromThisGroup(BusinessLogicException):
    default_detail = "Студента не состоит в данной группе"
    default_code = "student_not_from_this_group"
