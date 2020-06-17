[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![GitHub contributors](https://img.shields.io/github/contributors/kozlyuk/planner.svg)](https://GitHub.com/kozlyuk/planner/graphs/contributors/)
[![GitHub pull-requests closed](https://img.shields.io/github/issues-pr-closed/kozlyuk/planner.svg)](https://GitHub.com/kozlyuk/planner/pulls/)
[![Open Source Love svg1](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)
# Installing
1. install Python3
2. create virtual env ``` python3 -m venv /path/to/new/virtual/environment```
3. activate venv ``` source venv/bin/activate```
4. install dependencies ``` pip install -r requirements.txt ```
5. in folder planner create ```settings_local.py``` file
<p align="center"> content settings_local.py </p>

```python
SECRET_KEY = ''
DEBUG = True 
ALLOWED_HOSTS = ['*']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'your_db_name',
        'USER': 'db_user',
        'PASSWORD': 'password',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}
```
