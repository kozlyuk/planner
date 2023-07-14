EXECUTION_BADGE_COLORS = {
    'ToDo': '#8797de',
    'InProgress': '#6875b0',
    'Done': '#3c4b8c',
    'OnChecking': '#1a2b75',
    'OnCorrection': '#8797de',
    'OnHold': '#525561'
}

TASK_BADGE_COLORS = {
    # task EXEC_STATUS_CHOICES
    'ToDo': 'warning',
    'InProgress': 'info',
    'Done': 'success',
    'Sent': 'primary',
    'OnHold': 'primary',
    'Canceled': 'primary',
    # Warnings
    'ManualWarning': 'secondary',
    'Print': '-color1',             # static => assets => global => css => custom.css
    'Urgent': '-color__urgent',     # static => assets => global => css => custom.css
    'Correction': '-color2',        # static => assets => global => css => custom.css
}
