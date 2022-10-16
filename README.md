# ARQ Django admin

![](https://github.com/SlavaSkvortsov/arq-django-admin/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/SlavaSkvortsov/arq-django-admin/branch/master/graph/badge.svg)](https://codecov.io/gh/SlavaSkvortsov/arq-django-admin)
[![pypi](https://img.shields.io/pypi/v/arq-django-admin.svg)](https://pypi.python.org/pypi/arq-django-admin)
[![versions](https://img.shields.io/pypi/pyversions/arq-django-admin.svg)](https://github.com/SlavaSkvortsov/arq-django-admin)

Django admin dashboard for [arq](https://github.com/samuelcolvin/arq).
ARQ Django admin is a simple app that allows you to configure your queues in django's settings.py and show them in your admin dashboard.

# Installation
- Install `arq-django-admin` ([or download from PyPI](https://pypi.org/project/arq-django-admin/)):
```shell script
pip install arq-django-admin
```

- Add `arq_admin` to `INSTALLED_APPS` in `settings.py`:
```python
INSTALLED_APPS = (
    'arq_admin',
    # other apps
)
``` 
Make sure you added it before `django.contrib.admin`, otherwise you won't be able to see a link in the top right corner.

- Configure your queues in Django's `settings.py`:
```python
from arq.connections import RedisSettings
from arq.constants import default_queue_name


ARQ_QUEUES = {
    default_queue_name: RedisSettings(
        host='localhost',
        port=6379,
        database=0,
    ),
    'arq:another_queue_name': RedisSettings(),
}
```

- Include `arq_admin.urls` in your `urls.py`:
```python
from django.urls import include, path


urlpatterns = [
    # <...>
    path('arq/', include('arq_admin.urls')),
]
```

- If you use custom job serializer, you need to add deserializer to `settings.py`:
```python
ARQ_DESERIALIZER_BY_QUEUE = {
    'arq:another_queue_name': custom_job_deserializer,
}
```

- You can change timeout for job aborting:
```python
ARQ_JOB_ABORT_TIMEOUT = 10
```
