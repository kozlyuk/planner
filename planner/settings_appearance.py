EXECUTION_BADGE_COLORS = {
    'ToDo': '#ffc107',
    'InProgress': '#17a2b8',
    'Done': '#28a745',
    'OnChecking': '#007bff'
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
