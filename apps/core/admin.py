from django.contrib import admin


class BaseModelAdmin(admin.ModelAdmin):
    readonly_base_fields = ("created_at", "updated_at", "deleted_at")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if hasattr(self.model, "all_objects"):
            return self.model.all_objects.all()
        return queryset

    def get_readonly_fields(self, request, obj=None):
        model_fields = {field.name for field in self.model._meta.get_fields()}
        readonly_fields = [
            field_name
            for field_name in self.readonly_base_fields
            if field_name in model_fields
        ]
        return tuple(readonly_fields) + tuple(super().get_readonly_fields(request, obj))
