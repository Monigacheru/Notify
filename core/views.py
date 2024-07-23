import os
from django.shortcuts import render
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from decouple import config
import pandas as pd
from datetime import timedelta
from django.utils import timezone
import africastalking as at
from . import models
from . import forms

AFRICASTALKING_USERNAME = config("DJANGO_AFRICASTALKING_USERNAME")
AFRICASTALKING_API_KEY = config("DJANGO_AFRICASTALKING_API_KEY")
at.initialize(AFRICASTALKING_USERNAME, AFRICASTALKING_API_KEY)
SMS = at.SMS


def home(request):
    return render(request, "core/index.html")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories_count"] = models.Category.objects.count()
        context["contacts_count"] = models.Contact.objects.count()
        context["messages_count"] = models.Message.objects.count()

        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        current_week_messages = models.Message.objects.filter(
            created_at__range=[start_of_week, end_of_week]
        )
        context["current_week_messages"] = current_week_messages

        return context


class CategoryListView(LoginRequiredMixin, ListView):
    model = models.Category
    template_name = "categories/category_list.html"


class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = models.Category
    template_name = "categories/category_detail.html"


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = models.Category
    form_class = forms.Category
    template_name = "categories/category_form.html"
    success_url = reverse_lazy("core:category-list")

    def form_valid(self, form):
        form.instance.creator = self.request.user
        response = super().form_valid(form)
        instance = form.instance
        file_extension = os.path.splitext(instance.contacts_import_file.name)[1]

        if file_extension == ".csv":
            df = pd.read_csv(instance.contacts_import_file)
        elif file_extension == ".xlsx":
            df = pd.read_excel(instance.contacts_import_file)
        else:
            raise ValueError("Unsupported file format")

        # Print the columns for debugging purposes
        print(f"Columns in the uploaded file: {df.columns.tolist()}")

        required_columns = ["First Name", "Sur Name", "Phone Number"]
        if not all(col in df.columns for col in required_columns):
            raise ValueError("The uploaded file is missing required columns.")

        for _, row in df.iterrows():
            try:
                contact, created = models.Contact.objects.get_or_create(
                    first_name=row["First Name"].strip(),
                    last_name=row["Sur Name"].strip(),
                    phone_number=f"+{row['Phone Number']}".strip(),
                )
                models.CategoryContact.objects.get_or_create(
                    contact=contact,
                    category=instance,
                )
            except Exception as e:
                print(f"Error importing {row.get('Phone Number', 'unknown')}: {e}")

        return response


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = models.Category
    form_class = forms.Category
    template_name = "categories/category_form.html"
    success_url = reverse_lazy("core:category-list")


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = models.Category
    template_name = "categories/category_confirm_delete.html"
    success_url = reverse_lazy("core:category-list")


class ContactListView(LoginRequiredMixin, ListView):
    model = models.Contact
    template_name = "contacts/contact_list.html"


class ContactDetailView(LoginRequiredMixin, DetailView):
    model = models.Contact
    template_name = "contacts/contact_detail.html"


class ContactCreateView(LoginRequiredMixin, CreateView):
    model = models.Contact
    form_class = forms.Contact
    template_name = "contacts/contact_form.html"
    success_url = reverse_lazy("core:contact-list")


class ContactUpdateView(LoginRequiredMixin, UpdateView):
    model = models.Contact
    form_class = forms.Contact
    template_name = "contacts/contact_form.html"
    success_url = reverse_lazy("core:contact-list")


class ContactDeleteView(LoginRequiredMixin, DeleteView):
    model = models.Contact
    template_name = "contacts/contact_confirm_delete.html"
    success_url = reverse_lazy("core:contact-list")


class MessageListView(LoginRequiredMixin, ListView):
    model = models.Message
    template_name = "messages/message_list.html"


class MessageDetailView(LoginRequiredMixin, DetailView):
    model = models.Message
    template_name = "messages/message_detail.html"


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = models.Message
    form_class = forms.Message
    template_name = "messages/message_form.html"
    success_url = reverse_lazy("core:message-list")

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.sender = self.request.user
        instance.save()
        students = instance.category.contacts.all()

        for student in students:
            try:
                response = SMS.send(
                    instance.content, [str(student.contact.phone_number)]
                )
                print(response)
            except Exception as e:
                print(f"Uh oh we have a problem: {e}")

        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = models.Message
    form_class = forms.Message
    template_name = "messages/message_form.html"
    success_url = reverse_lazy("core:message-list")


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = models.Message
    template_name = "messages/message_confirm_delete.html"
    success_url = reverse_lazy("core:message-list")
