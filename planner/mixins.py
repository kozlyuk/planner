import json
from django.forms.models import model_to_dict


class ModelDiffMixin(object):
    """
    A model mixin that tracks model fields' values and provide some useful api
    to know what fields have been changed.
    """

    def __init__(self, *args, **kwargs):
        super(ModelDiffMixin, self).__init__(*args, **kwargs)
        self.__initial = self._dict

    @property
    def diff(self):
        d1 = self.__initial
        d2 = self._dict
        diffs = [(k, (v, d2[k])) for k, v in d1.items() if v != d2[k]]
        return dict(diffs)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return self.diff.keys()

    def get_field_diff(self, field_name):
        """
        Returns a diff for field if it's changed and None otherwise.
        """
        return self.diff.get(field_name, None)

    def save(self, *args, **kwargs):
        """
        Saves model and set initial state.
        """
        super(ModelDiffMixin, self).save(*args, **kwargs)
        self.__initial = self._dict

    @property
    def _dict(self):
        return model_to_dict(self, fields=[field.name for field in
                             self._meta.fields])

    @property
    def diff_str(self):
        diff_str = f'Змінені поля: '
        changed = False

        for key, value in self.diff.items():
            changed = True
            field = self._meta.get_field(key)
            if field.choices is not None:
                value_str = ' -> '.join(map(lambda x: '' if x is None else dict(field.choices)[x], value))
            else:
                value_str = ' -> '.join(map(lambda x: '' if x is None else str(x), value))
            diff_str += f'{field.verbose_name}: {value_str}, '

        return diff_str[:-2] if changed else None
