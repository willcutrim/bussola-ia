from django import forms


class BootstrapFormMixin:
    """Aplica classes Bootstrap padrao sem acoplar os forms ao template."""

    base_input_class = "form-control"
    base_select_class = "form-select"
    base_checkbox_class = "form-check-input"
    base_textarea_class = "form-control"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for bound_name, field in self.fields.items():
            widget = field.widget
            current_classes = widget.attrs.get("class", "").split()

            if isinstance(widget, forms.CheckboxInput):
                classes_to_add = self.base_checkbox_class.split()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                classes_to_add = self.base_select_class.split()
            elif isinstance(widget, forms.Textarea):
                classes_to_add = self.base_textarea_class.split()
                widget.attrs.setdefault("rows", 4)
            else:
                classes_to_add = self.base_input_class.split()

            for css_class in classes_to_add:
                if css_class not in current_classes:
                    current_classes.append(css_class)

            widget.attrs["class"] = " ".join(filter(None, current_classes))
            widget.attrs.setdefault("placeholder", field.label or bound_name.replace("_", " ").title())

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.pop("placeholder", None)
