from django import forms
from django_json_widget.widgets import JSONEditorWidget
from .models import YourModel


class YourForm(forms.ModelForm):
    class Meta:
        model = YourModel

        fields = ('jsonfield',)

        widgets = {
            'jsonfield': JSONEditorWidget
        }