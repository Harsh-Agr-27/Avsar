import importlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.urls import reverse

from .models import Opportunity, ScholarshipProfile


class ScholarshipProfileFlowTests(TestCase):
    def test_every_page_uses_shared_left_brand_right_tagline_footer(self):
        pages = (
            reverse('pages:home'),
            reverse('pages:login'),
            reverse('pages:register'),
            reverse('pages:opportunities'),
            reverse('pages:schemes'),
            reverse('pages:scholarships'),
            reverse('pages:internships'),
        )
        user = get_user_model().objects.create_user(
            username='footer@example.com',
            email='footer@example.com',
            password='A-Footer-Page-Password-218!',
        )
        ScholarshipProfile.objects.create(user=user)
        self.client.force_login(user)
        pages += (reverse('pages:profile'),)

        for page_url in pages:
            with self.subTest(page=page_url):
                response = self.client.get(page_url)
                self.assertEqual(response.status_code, 200)
                content = response.content.decode()
                self.assertEqual(content.count('class="site-footer"'), 1)
                self.assertLess(
                    content.index('class="brand footer-brand"'),
                    content.index('class="footer-tagline"'),
                )
                self.assertIn(
                    'Explore thoughtfully. Always confirm details with the official provider.',
                    content,
                )

    def test_opportunity_pages_render_and_are_linked_from_home(self):
        pages = (
            ('pages:opportunities', 'All opportunities'),
            ('pages:schemes', 'Government schemes'),
            ('pages:scholarships', 'Scholarships'),
            ('pages:internships', 'Internships'),
        )

        home_response = self.client.get(reverse('pages:home'))
        self.assertEqual(home_response.status_code, 200)
        self.assertEqual(home_response.content.count(b'class="category-card '), 3)

        for route_name, page_title in pages:
            with self.subTest(page=page_title):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'<h1 id="page-title">{page_title}</h1>', html=True)
                self.assertContains(home_response, reverse(route_name))
                self.assertContains(response, reverse(route_name))

    def test_signup_saves_account_and_opens_optional_profile(self):
        response = self.client.post(reverse('pages:register'), {
            'full_name': 'Scholarship Applicant',
            'email': 'applicant@example.com',
            'password': 'A-Strong-Unique-Password-481!',
            'confirm_password': 'A-Strong-Unique-Password-481!',
        })

        self.assertRedirects(response, reverse('pages:profile'))
        user = get_user_model().objects.get(email='applicant@example.com')
        self.assertTrue(user.check_password('A-Strong-Unique-Password-481!'))
        self.assertTrue(ScholarshipProfile.objects.filter(user=user).exists())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        profile_response = self.client.get(reverse('pages:profile'))
        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, 'Everything on this page is optional')

    def test_profile_is_saved_and_prefilled_after_a_later_login(self):
        user = get_user_model().objects.create_user(
            username='learner@example.com',
            email='learner@example.com',
            password='Another-Strong-Password-731!',
        )
        profile = ScholarshipProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(reverse('pages:profile'), {
            'domicile_state': 'maharashtra',
            'date_of_birth': '2005-04-20',
            'gender': 'female',
            'community_category': 'obc',
            'parent_family_annual_income': '125000.00',
            'current_course_name': 'Bachelor of Science',
            'current_course_year': '2nd year',
            'class_tenth_passing_year': '2021',
            'class_tenth_percentage': '88.50',
        })
        self.assertRedirects(response, reverse('pages:profile'))

        profile.refresh_from_db()
        self.assertEqual(profile.domicile_state, 'maharashtra')
        self.assertEqual(profile.parent_family_annual_income, 125000)
        expected_age = date.today().year - 2005 - (
            (date.today().month, date.today().day) < (4, 20)
        )
        self.assertEqual(profile.age, expected_age)

        self.client.post(reverse('pages:logout'))
        login_response = self.client.post(reverse('pages:login'), {
            'email': 'LEARNER@example.com',
            'password': 'Another-Strong-Password-731!',
        })
        self.assertRedirects(login_response, reverse('pages:profile'))
        response = self.client.get(reverse('pages:profile'))
        self.assertContains(response, 'value="Bachelor of Science"')
        self.assertContains(response, 'value="125000.00"')
        self.assertContains(response, 'Age calculated from your date of birth')

    def test_profile_is_private_and_future_birth_date_is_rejected(self):
        user = get_user_model().objects.create_user(
            username='private@example.com',
            email='private@example.com',
            password='A-Private-Password-835!',
        )
        profile = ScholarshipProfile.objects.create(user=user)

        response = self.client.get(reverse('pages:profile'))
        self.assertRedirects(
            response,
            f'{reverse("pages:login")}?next={reverse("pages:profile")}',
        )

        self.client.force_login(user)
        response = self.client.post(reverse('pages:profile'), {
            'date_of_birth': '2999-01-01',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Date of birth cannot be in the future.')
        profile.refresh_from_db()
        self.assertIsNone(profile.date_of_birth)

    def test_skip_profile_leaves_optional_details_blank(self):
        user = get_user_model().objects.create_user(
            username='skip@example.com',
            email='skip@example.com',
            password='A-Skip-Profile-Password-639!',
        )
        ScholarshipProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(reverse('pages:profile'), {'skip_profile': '1'})

        self.assertRedirects(response, reverse('pages:home'))
        profile = ScholarshipProfile.objects.get(user=user)
        self.assertEqual(profile.domicile_state, '')
        self.assertIsNone(profile.date_of_birth)


class OpportunityCatalogTests(TestCase):
    def setUp(self):
        # The shipped catalogue is loaded by a data migration; these tests use
        # a hand-built catalogue instead.
        Opportunity.objects.all().delete()

    def create_opportunity(self, opportunity_id, category):
        return Opportunity.objects.create(
            id=opportunity_id,
            opportunity_type='scheme',
            title=f'{category} Student Support',
            provider='Avsar Test Provider',
            image='https://example.com/opportunity.jpg',
            benefit='Financial support',
            deadline='30 Nov 2026',
            verified='Official portal',
            mode='Online',
            min_education='12th',
            min_marks=80,
            max_income=450000,
            category=category,
            gender='Female',
            state='Maharashtra',
            min_age=17,
            max_age=25,
            pwd_only=False,
            skills='[]',
            description='Support for eligible students.',
            eligibility='12th passed; family income under the limit.',
            documents='',
            official_link='https://example.com/details',
        )

    def test_incomplete_profiles_are_prompted_and_catalogue_pages_filter_records(self):
        scheme = self.create_opportunity('scheme-1', 'OBC')
        Opportunity.objects.create(
            id='internship-1',
            opportunity_type='internship',
            title='Student Internship',
            provider='Avsar Test Provider',
            image='https://example.com/internship.jpg',
            benefit='Experience',
            deadline='30 Nov 2026',
            description='An internship for students.',
            official_link='https://example.com/internship',
        )

        guest_response = self.client.get(reverse('pages:schemes'))
        self.assertContains(guest_response, 'Sign in and complete your profile')
        self.assertContains(guest_response, 'opportunity.jpg')
        self.assertContains(guest_response, scheme.title)
        self.assertEqual(guest_response.content.count(b'class="opportunity-card"'), 1)
        self.assertNotContains(guest_response, 'Back to top')
        self.assertContains(
            guest_response,
            reverse('pages:opportunity_detail', args=[scheme.pk]),
        )

        all_response = self.client.get(reverse('pages:opportunities'))
        self.assertEqual(all_response.content.count(b'class="opportunity-card"'), 2)

        user = get_user_model().objects.create_user(
            username='incomplete@example.com',
            email='incomplete@example.com',
            password='A-Complete-Profile-Password-573!',
        )
        ScholarshipProfile.objects.create(user=user)
        self.client.force_login(user)
        incomplete_response = self.client.get(reverse('pages:schemes'))
        self.assertContains(incomplete_response, 'Complete your profile to see an eligibility estimate')
        self.assertContains(incomplete_response, reverse('pages:profile'))

    def test_completed_profile_gets_eligibility_results_from_structured_criteria(self):
        matching = self.create_opportunity('scheme-match', 'OBC')
        self.create_opportunity('scheme-category-mismatch', 'SC')
        user = get_user_model().objects.create_user(
            username='complete@example.com',
            email='complete@example.com',
            password='A-Complete-Profile-Password-641!',
        )
        ScholarshipProfile.objects.create(
            user=user,
            domicile_state='maharashtra',
            date_of_birth=date(2005, 4, 20),
            gender='female',
            community_category='obc',
            has_disability=False,
            parent_family_annual_income=200000,
            education_level='UG',
            previous_marks=90,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('pages:schemes'))

        self.assertContains(response, 'Meets the listed eligibility criteria')
        self.assertContains(response, 'Does not meet all listed criteria')
        self.assertContains(response, matching.image)
        self.assertContains(response, 'Community category: SC')

    def test_opportunity_detail_shows_description_eligibility_documents_and_deadline(self):
        opportunity = self.create_opportunity('scheme-detail', 'OBC')
        opportunity.eligibility = '["Be enrolled in an approved course", "Meet the income limit"]'
        opportunity.documents = '["Income certificate", "Academic transcript"]'
        opportunity.save()

        response = self.client.get(
            reverse('pages:opportunity_detail', args=[opportunity.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, opportunity.description)
        self.assertContains(response, 'Eligibility details')
        self.assertContains(response, 'Be enrolled in an approved course')
        self.assertContains(response, 'Documents required')
        self.assertContains(response, 'Income certificate')
        self.assertContains(response, 'Last application date: 30 Nov 2026')
        self.assertContains(response, 'Sign in and complete your profile')
        self.assertNotContains(response, 'Back to top')


class VercelServicesConfigTests(TestCase):
    """Guard the Vercel Services wiring (vercel.json + service requirements).

    `vercel.json` lives at the repository root, one directory above `manage.py`.
    """

    repo_root = Path(settings.BASE_DIR).parent

    def test_single_django_service_routed_from_the_public_catch_all(self):
        config = json.loads((self.repo_root / 'vercel.json').read_text())

        self.assertEqual(list(config['services']), ['avsar'])
        service = config['services']['avsar']
        # The service root must be the directory holding manage.py: Vercel only
        # searches manage.py in the service root and its immediate children,
        # and the repo root would nest the app two levels down.
        self.assertEqual(service['root'], 'Avsar')
        self.assertEqual(service['framework'], 'django')

        # The app is a single Django project, so it is the only public entry
        # point and needs no bindings: there is no other service to call.
        self.assertEqual(
            config['rewrites'],
            [{'source': '/(.*)', 'destination': {'service': 'avsar'}}],
        )
        self.assertNotIn('bindings', service)

    def test_build_and_runtime_keys_are_not_set_at_the_top_level(self):
        config = json.loads((self.repo_root / 'vercel.json').read_text())

        # In services mode these belong to a service, not to the project.
        for key in (
            'functions',
            'installCommand',
            'buildCommand',
            'devCommand',
            'ignoreCommand',
            'outputDirectory',
            'framework',
        ):
            self.assertNotIn(key, config)

    def test_service_requirements_are_self_contained(self):
        service_requirements = (
            self.repo_root / 'Avsar' / 'requirements.txt'
        ).read_text()

        # Vercel installs inside the service root and cannot resolve includes,
        # so `-r ../requirements.txt` would break the build.
        requirement_lines = [
            line.strip()
            for line in service_requirements.splitlines()
            if line.strip() and not line.strip().startswith('#')
        ]
        for line in requirement_lines:
            self.assertNotRegex(line, r'^(-r|--requirement)\b')

        def normalise(text):
            return {
                line.strip().lower().replace(' ', '')
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith('#')
            }

        self.assertEqual(
            normalise(service_requirements),
            normalise((self.repo_root / 'requirements.txt').read_text()),
        )

    def test_settings_import_without_a_secret_key_so_the_build_can_run(self):
        """Vercel imports settings during the build, before secrets apply.

        The build reads settings to locate the WSGI entrypoint and to run
        `collectstatic`. Requiring DJANGO_SECRET_KEY at import time failed the
        deployment with DJANGO_SETTINGS_FAILED, so the requirement now lives in
        the request path (Avsar.bootstrap.require_secret_key).
        """
        script = (
            'import os, runpy, sys\n'
            'os.environ.pop("DJANGO_SECRET_KEY", None)\n'
            'os.environ["VERCEL_ENV"] = "production"\n'
            'import django.conf\n'
            'import Avsar.settings as settings\n'
            'assert settings.SECRET_KEY == "", settings.SECRET_KEY\n'
            'assert settings.WSGI_APPLICATION == "Avsar.wsgi.application"\n'
        )
        result = subprocess.run(
            [sys.executable, '-c', script],
            cwd=str(Path(settings.BASE_DIR)),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_entrypoints_require_a_secret_key_before_serving_requests(self):
        """The check must still fire where it matters: at request time."""
        settings_module = importlib.import_module('Avsar.settings')

        for module in ('Avsar/Avsar/wsgi.py', 'Avsar/Avsar/asgi.py'):
            with self.subTest(module=module):
                source = (self.repo_root / module).read_text()
                self.assertIn('require_secret_key()', source)

        from Avsar.bootstrap import MISSING_SECRET_KEY_MESSAGE, require_secret_key

        # Simulate a production deployment that never got the variable set.
        with mock.patch.object(settings_module, 'SECRET_KEY', ''):
            with mock.patch.object(settings, 'DEBUG', False):
                with self.assertRaisesMessage(
                    ImproperlyConfigured, MISSING_SECRET_KEY_MESSAGE
                ):
                    require_secret_key()
