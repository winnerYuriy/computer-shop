from django import forms
from django_json_widget.widgets import JSONEditorWidget
from .models import Product


class ProductAttributesForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('attributes',)

        widgets = {
            'attributes': JSONEditorWidget
        }