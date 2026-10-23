from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from django.urls import reverse_lazy
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", LoginView.as_view(template_name="learning/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", LogoutView.as_view(next_page=reverse_lazy("home")), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("upload/", views.upload_document, name="upload"),
    path("documents/<int:pk>/", views.document_detail, name="document_detail"),
    path("documents/<int:pk>/delete/", views.delete_document, name="delete_document"),
    path("documents/<int:pk>/ask/", views.ask_question, name="ask_question"),
    path("documents/<int:pk>/summary/", views.summary, name="summary"),
    path("documents/<int:pk>/flashcards/", views.flashcards, name="flashcards"),
    path("documents/<int:pk>/quiz/", views.quiz, name="quiz"),
    path("progress/", views.progress, name="progress"),
]
