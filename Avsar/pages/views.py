import json
import re

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import LoginForm, ScholarshipProfileForm, SignupForm
from .models import Opportunity, ScholarshipProfile


OPPORTUNITY_PAGES = {
    'all': {
        'title': 'All opportunities',
        'eyebrow': 'Explore opportunities',
        'description': 'Explore scholarships, government schemes, and internships together in one place.',
    },
    'schemes': {
        'title': 'Government schemes',
        'eyebrow': 'Support and benefits',
        'description': 'Explore public programmes and benefits for you and your family.',
    },
    'scholarships': {
        'title': 'Scholarships',
        'eyebrow': 'Education support',
        'description': 'Find financial support that can help you continue your education.',
    },
    'internships': {
        'title': 'Internships',
        'eyebrow': 'Career experience',
        'description': 'Discover practical experience and take your first career steps.',
    },
}

PROFILE_ELIGIBILITY_FIELDS = (
    'domicile_state',
    'date_of_birth',
    'gender',
    'community_category',
    'has_disability',
    'parent_family_annual_income',
    'education_level',
    'previous_marks',
)

EDUCATION_LEVELS = {
    '10th': 0,
    '11th': 1,
    '12th': 2,
    'diploma': 2,
    'ug': 3,
    'pg': 4,
}


def home(request):
    return render(request, 'pages/home.html')


def _normalise(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())


def _profile_is_ready(profile):
    return all(
        getattr(profile, field) is not None
        and getattr(profile, field) != ''
        for field in PROFILE_ELIGIBILITY_FIELDS
    )


def _meets_eligibility(profile, opportunity):
    reasons = []
    age = profile.age
    if opportunity.min_age is not None and (age is None or age < opportunity.min_age):
        reasons.append(f'Minimum age: {opportunity.min_age}')
    if opportunity.max_age is not None and (age is None or age > opportunity.max_age):
        reasons.append(f'Maximum age: {opportunity.max_age}')
    if opportunity.min_marks is not None and (
        profile.previous_marks is None
        or profile.previous_marks < opportunity.min_marks
    ):
        reasons.append(f'Minimum marks: {opportunity.min_marks:g}%')
    if opportunity.max_income is not None and (
        profile.parent_family_annual_income is None
        or profile.parent_family_annual_income > opportunity.max_income
    ):
        reasons.append(f'Maximum family income: ₹{opportunity.max_income:,}')

    required_education = EDUCATION_LEVELS.get(_normalise(opportunity.min_education))
    student_education = EDUCATION_LEVELS.get(_normalise(profile.education_level))
    if required_education is not None and (
        student_education is None or student_education < required_education
    ):
        reasons.append(f'Minimum education: {opportunity.min_education}')

    if opportunity.category and _normalise(opportunity.category) != 'all' and (
        _normalise(profile.community_category) != _normalise(opportunity.category)
    ):
        reasons.append(f'Community category: {opportunity.category}')
    if opportunity.gender and _normalise(opportunity.gender) != 'all' and (
        _normalise(profile.gender) != _normalise(opportunity.gender)
    ):
        reasons.append(f'Gender: {opportunity.gender}')
    if opportunity.state and _normalise(opportunity.state) not in {'all', 'central'} and (
        _normalise(profile.domicile_state) != _normalise(opportunity.state)
    ):
        reasons.append(f'Domicile state: {opportunity.state}')
    if opportunity.pwd_only and profile.has_disability is not True:
        reasons.append('PwD status')

    required_skills = json.loads(opportunity.skills or '[]')
    if required_skills:
        student_skills = {_normalise(skill) for skill in profile.skills}
        missing_skills = [
            skill for skill in required_skills
            if _normalise(skill) not in student_skills
        ]
        if missing_skills:
            reasons.append(f'Required skills: {", ".join(missing_skills)}')

    return not reasons, reasons


def _eligibility_for_request(request, opportunity):
    profile = None
    profile_ready = False
    if request.user.is_authenticated:
        profile = getattr(request.user, 'scholarship_profile', None)
        profile_ready = profile is not None and _profile_is_ready(profile)

    eligible = False
    reasons = []
    if profile_ready:
        eligible, reasons = _meets_eligibility(profile, opportunity)
    return {
        'profile_ready': profile_ready,
        'eligible': eligible,
        'reasons': reasons,
        'is_authenticated': request.user.is_authenticated,
    }


def _parse_detail_list(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if item]
    if isinstance(parsed, str) and parsed:
        return [parsed]
    return []


def opportunity_page(request, page_type):
    page = OPPORTUNITY_PAGES.get(page_type)
    if page is None:
        raise Http404

    opportunities = Opportunity.objects.all()
    if page_type != 'all':
        opportunities = opportunities.filter(opportunity_type=page_type[:-1])

    profile = None
    profile_ready = False
    if request.user.is_authenticated:
        profile = getattr(request.user, 'scholarship_profile', None)
        profile_ready = profile is not None and _profile_is_ready(profile)

    opportunity_results = []
    for opportunity in opportunities:
        eligible = False
        reasons = []
        if profile_ready:
            eligible, reasons = _meets_eligibility(profile, opportunity)
        opportunity_results.append({
            'opportunity': opportunity,
            'eligible': eligible,
            'reasons': reasons,
        })

    return render(request, 'pages/opportunity_page.html', {
        **page,
        'opportunities': opportunity_results,
        'profile_ready': profile_ready,
        'is_authenticated': request.user.is_authenticated,
    })


def opportunity_detail(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
    return render(request, 'pages/opportunity_detail.html', {
        'opportunity': opportunity,
        'eligibility': _eligibility_for_request(request, opportunity),
        'eligibility_details': _parse_detail_list(opportunity.eligibility),
        'required_documents': _parse_detail_list(opportunity.documents),
    })


def login_view(request):
    form = LoginForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().casefold()
        user = authenticate(
            request,
            username=email,
            password=form.cleaned_data['password'],
        )
        if user is not None:
            auth_login(request, user)
            return redirect('pages:profile')
        form.add_error(None, 'The email or password is incorrect.')

    return render(request, 'pages/login.html', {'form': form})


def register(request):
    form = SignupForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username=email,
                email=email,
                first_name=form.cleaned_data['full_name'],
                password=form.cleaned_data['password'],
            )
            ScholarshipProfile.objects.create(user=user)
        auth_login(request, user)
        return redirect('pages:profile')

    return render(request, 'pages/register.html', {'form': form})


@login_required(login_url='pages:login')
def profile(request):
    scholarship_profile, _ = ScholarshipProfile.objects.get_or_create(user=request.user)
    form = ScholarshipProfileForm(
        request.POST if request.method == 'POST' else None,
        instance=scholarship_profile,
    )
    if request.method == 'POST' and 'skip_profile' in request.POST:
        return redirect('pages:home')
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your scholarship profile has been saved.')
        return redirect('pages:profile')

    return render(request, 'pages/profile.html', {
        'form': form,
        'profile': scholarship_profile,
    })


@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect('pages:home')
