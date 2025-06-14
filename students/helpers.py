def get_diff_month(start_date, end_date):
    return (end_date.year - start_date.year) * 12 + end_date.month - start_date.month