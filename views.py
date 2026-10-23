
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SignUpForm, UploadDocumentForm
from .learning_utils import (
    extract_pdf_text,
    summarize,
    answer_question,
    make_flashcards,
    make_quiz,
)
from .models import StudyDocument, StudyActivity


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    return render(request, "learning/home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignUpForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(
            request,
            "Welcome to StudyMate! Your learning space is ready."
        )
        return redirect("dashboard")

    return render(request, "learning/signup.html", {"form": form})


@login_required
def dashboard(request):
    docs = StudyDocument.objects.filter(
        owner=request.user
    ).order_by("-uploaded_at")

    activities = StudyActivity.objects.filter(
        owner=request.user
    ).select_related("document").order_by("-created_at")[:6]

    stats = {
        "documents": docs.count(),
        "activities": StudyActivity.objects.filter(
            owner=request.user
        ).count(),
        "quizzes": StudyActivity.objects.filter(
            owner=request.user,
            activity_type="quiz"
        ).count(),
        "avg_score": None,
    }

    scores = list(
        StudyActivity.objects.filter(
            owner=request.user,
            activity_type="quiz",
            score__isnull=False
        ).values_list("score", flat=True)
    )

    if scores:
        stats["avg_score"] = round(sum(scores) / len(scores))

    query = request.GET.get("q", "").strip()

    if query:
        docs = docs.filter(title__icontains=query)

    return render(
        request,
        "learning/dashboard.html",
        {
            "documents": docs,
            "activities": activities,
            "stats": stats,
            "query": query,
        }
    )


@login_required
def upload_document(request):
    form = UploadDocumentForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == "POST" and form.is_valid():
        doc = form.save(commit=False)
        doc.owner = request.user
        doc.save()

        try:
            with doc.pdf_file.open("rb") as pdf:
                doc.extracted_text = extract_pdf_text(pdf)

            doc.save(update_fields=["extracted_text"])

            messages.success(
                request,
                "PDF uploaded and processed successfully."
            )

        except Exception:
            doc.delete()
            messages.error(
                request,
                "Could not read this PDF. Please upload a valid PDF file."
            )
            return redirect("upload")

        return redirect("document_detail", pk=doc.pk)

    return render(request, "learning/upload.html", {"form": form})


@login_required
def document_detail(request, pk):
    doc = get_object_or_404(
        StudyDocument,
        pk=pk,
        owner=request.user
    )

    text_preview = (doc.extracted_text or "")[:3500]

    return render(
        request,
        "learning/document_detail.html",
        {
            "document": doc,
            "text_preview": text_preview,
        }
    )


@login_required
def delete_document(request, pk):
    doc = get_object_or_404(
        StudyDocument,
        pk=pk,
        owner=request.user
    )

    if request.method == "POST":
        doc.delete()
        messages.success(request, "Study material deleted.")
        return redirect("dashboard")

    return render(
        request,
        "learning/confirm_delete.html",
        {"document": doc}
    )


@login_required
def ask_question(request, pk):
    doc = get_object_or_404(
        StudyDocument,
        pk=pk,
        owner=request.user
    )

    answer = None
    question = ""

    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if question:
            answer = answer_question(
                doc.extracted_text or "",
                question
            )

            StudyActivity.objects.create(
                owner=request.user,
                document=doc,
                activity_type="question"
            )

    return render(
        request,
        "learning/ask.html",
        {
            "document": doc,
            "answer": answer,
            "question": question,
        }
    )


@login_required
def summary(request, pk):
    doc = get_object_or_404(
        StudyDocument,
        pk=pk,
        owner=request.user
    )

    result = summarize(doc.extracted_text or "")

    StudyActivity.objects.create(
        owner=request.user,
        document=doc,
        activity_type="summary"
    )

    return render(
        request,
        "learning/summary.html",
        {
            "document": doc,
            "summary": result,
        }
    )


@login_required
def flashcards(request, pk):
    doc = get_object_or_404(
        StudyDocument,
        pk=pk,
        owner=request.user
    )

    cards = make_flashcards(doc.extracted_text or "")

    StudyActivity.objects.create(
        owner=request.user,
        document=doc,
        activity_type="flashcards"
    )

    return render(
        request,
        "learning/flashcards.html",
        {
            "document": doc,
            "cards": cards,
        }
    )


@login_required
def quiz(request, pk):
    doc = get_object_or_404(
        StudyDocument,
        pk=pk,
        owner=request.user
    )

    questions = make_quiz(doc.extracted_text or "")

    if request.method == "POST":
        score = 0
        answers = {}

        for i, item in enumerate(questions):
            selected = request.POST.get(f"q{i}", "")
            answers[i] = selected

            if selected.lower() == item["answer"].lower():
                score += 1

        total = len(questions)
        percent = round(score * 100 / total) if total else 0

        StudyActivity.objects.create(
            owner=request.user,
            document=doc,
            activity_type="quiz",
            score=percent
        )

        return render(
            request,
            "learning/quiz_result.html",
            {
                "document": doc,
                "questions": questions,
                "answers": answers,
                "score": score,
                "total": total,
                "percent": percent,
            }
        )

    return render(
        request,
        "learning/quiz.html",
        {
            "document": doc,
            "questions": questions,
        }
    )


@login_required
def progress(request):
    activities = StudyActivity.objects.filter(
        owner=request.user
    ).select_related("document").order_by("-created_at")

    breakdown = (
        StudyActivity.objects.filter(owner=request.user)
        .values("activity_type")
        .annotate(total=Count("id"))
        .order_by()
    )

    return render(
        request,
        "learning/progress.html",
        {
            "activities": activities,
            "breakdown": breakdown,
        }
    )