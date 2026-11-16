"""Forms for collecting login and account-creation input."""

from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from .models import ScholarshipProfile


class LoginForm(forms.Form):
    """Validate the email and password entered on the login page."""

    email = forms.EmailField(
        label='Email address',
        max_length=150,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'placeholder': 'you@example.com',
            'class': 'form-control',
        }),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'placeholder': 'Your password',
            'class': 'form-control',
        }),
    )


class SignupForm(forms.Form):
    """Validate new account details before a view creates the user."""

    full_name = forms.CharField(
        label='Full name',
        max_length=150,
        widget=forms.TextInput(attrs={
            'autocomplete': 'name',
            'placeholder': 'Your full name',
            'class': 'form-control',
        }),
    )
    email = forms.EmailField(
        label='Email address',
        max_length=150,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'placeholder': 'you@example.com',
            'class': 'form-control',
        }),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'placeholder': 'Create a password',
            'class': 'form-control',
        }),
    )
    confirm_password = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'placeholder': 'Enter the password again',
            'class': 'form-control',
        }),
    )

    def clean_email(self):
        """Normalize email and reject an address already used by an account."""
        email = self.cleaned_data['email'].strip().casefold()
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        """Check that the passwords match and satisfy Django's password rules."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirmation = cleaned_data.get('confirm_password')

        if password and confirmation and password != confirmation:
            self.add_error('confirm_password', 'The passwords do not match.')

        if password:
            user_model = get_user_model()
            candidate_user = user_model(
                username=cleaned_data.get('email', ''),
                email=cleaned_data.get('email', ''),
                first_name=cleaned_data.get('full_name', ''),
            )
            try:
                validate_password(password, user=candidate_user)
            except ValidationError as error:
                self.add_error('password', error)

        return cleaned_data


class ScholarshipProfileForm(ModelForm):
    """Collect optional details used to match users with scholarships."""

    preferred_opportunity_types = forms.MultipleChoiceField(
        choices=ScholarshipProfile.OpportunityType.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Types of opportunity you want to see',
    )
    skills = forms.MultipleChoiceField(
        choices=ScholarshipProfile.SKILL_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Skills and interests',
    )

    class Meta:
        model = ScholarshipProfile
        fields = [
            'domicile_state',
            'date_of_birth',
            'gender',
            'community_category',
            'has_disability',
            'parent_family_annual_income',
            'preferred_opportunity_types',
            'education_level',
            'current_course_name',
            'previous_marks',
            'skills',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'autocomplete': 'bday',
            }),
            'parent_family_annual_income': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01',
            }),
            'previous_marks': forms.NumberInput(attrs={
                'min': '0',
                'max': '100',
                'step': '0.01',
            }),
        }
        labels = {
            'domicile_state': 'Domicile State / UT',
            'date_of_birth': 'Date of birth',
            'has_disability': 'Do you have a disability (PwD)?',
            'parent_family_annual_income': 'Combined annual family income (₹)',
            'education_level': 'Current education level',
            'current_course_name': 'Current course name',
            'previous_marks': 'Previous qualifying marks (%)',
        }

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > date.today():
            raise ValidationError('Date of birth cannot be in the future.')
        return date_of_birth