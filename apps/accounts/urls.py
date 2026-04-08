from django.urls import path

from .views import (
    AccountLoginView,
    AccountLogoutView,
    AccountSignupView,
    UserCreateView,
    UserDeleteView,
    UserDetailView,
    UserListView,
    UserUpdateView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", AccountLoginView.as_view(), name="login"),
    path("logout/", AccountLogoutView.as_view(), name="logout"),
    path("cadastro/", AccountSignupView.as_view(), name="signup"),
    path("", UserListView.as_view(), name="list"),
    path("novo/", UserCreateView.as_view(), name="create"),
    path("<int:pk>/", UserDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", UserUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", UserDeleteView.as_view(), name="delete"),
]
