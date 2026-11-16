from datetime import date

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ScholarshipProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        TRANSGENDER = 'transgender', 'Transgender'

    class CommunityCategory(models.TextChoices):
        GENERAL = 'general', 'General'
        EWS = 'ews', 'EWS'
        OBC = 'obc', 'OBC'
        SC = 'sc', 'SC'
        ST = 'st', 'ST'

    class EducationLevel(models.TextChoices):
        TENTH = '10th', 'Class 10'
        ELEVENTH = '11th', 'Class 11'
        TWELFTH = '12th', 'Class 12'
        DIPLOMA = 'Diploma', 'Diploma'
        UNDERGRADUATE = 'UG', 'Undergraduate (UG)'
        POSTGRADUATE = 'PG', 'Postgraduate (PG)'

    class OpportunityType(models.TextChoices):
        SCHOLARSHIP = 'scholarship', 'Scholarship'
        SCHEME = 'scheme', 'Scheme'
        INTERNSHIP = 'internship', 'Internship'

    SKILL_CHOICES = (
        ('Communication', 'Communication'),
        ('Excel', 'Excel'),
        ('Figma', 'Figma'),
        ('HTML/CSS', 'HTML/CSS'),
        ('JavaScript', 'JavaScript'),
        ('Operations', 'Operations'),
        ('Python', 'Python'),
        ('Research', 'Research'),
        ('SQL', 'SQL'),
        ('Statistics', 'Statistics'),
        ('Writing', 'Writing'),
    )

    INDIAN_STATES_AND_UTS = (
        ('andhra_pradesh', 'Andhra Pradesh'),
        ('arunachal_pradesh', 'Arunachal Pradesh'),
        ('assam', 'Assam'),
        ('bihar', 'Bihar'),
        ('chhattisgarh', 'Chhattisgarh'),
        ('goa', 'Goa'),
        ('gujarat', 'Gujarat'),
        ('haryana', 'Haryana'),
        ('himachal_pradesh', 'Himachal Pradesh'),
        ('jharkhand', 'Jharkhand'),
        ('karnataka', 'Karnataka'),
        ('kerala', 'Kerala'),
        ('madhya_pradesh', 'Madhya Pradesh'),
        ('maharashtra', 'Maharashtra'),
        ('manipur', 'Manipur'),
        ('meghalaya', 'Meghalaya'),
        ('mizoram', 'Mizoram'),
        ('nagaland', 'Nagaland'),
        ('odisha', 'Odisha'),
        ('punjab', 'Punjab'),
        ('rajasthan', 'Rajasthan'),
        ('sikkim', 'Sikkim'),
        ('tamil_nadu', 'Tamil Nadu'),
        ('telangana', 'Telangana'),
        ('tripura', 'Tripura'),
        ('uttar_pradesh', 'Uttar Pradesh'),
        ('uttarakhand', 'Uttarakhand'),
        ('west_bengal', 'West Bengal'),
        ('andaman_nicobar', 'Andaman and Nicobar Islands'),
        ('chandigarh', 'Chandigarh'),
        ('dadra_nagar_haveli_daman_diu', 'Dadra and Nagar Haveli and Daman and Diu'),
        ('delhi', 'Delhi'),
        ('jammu_kashmir', 'Jammu and Kashmir'),
        ('ladakh', 'Ladakh'),
        ('lakshadweep', 'Lakshadweep'),
        ('puducherry', 'Puducherry'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scholarship_profile',
    )

    domicile_state = models.CharField(max_length=40, choices=INDIAN_STATES_AND_UTS, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    community_category = models.CharField(max_length=20, choices=CommunityCategory.choices, blank=True)
    has_disability = models.BooleanField(null=True, blank=True)
    parent_family_annual_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    preferred_opportunity_types = models.JSONField(default=list, blank=True)
    education_level = models.CharField(max_length=20, choices=EducationLevel.choices, blank=True)
    current_course_name = models.CharField(max_length=200, blank=True)
    previous_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    skills = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f'Scholarship profile for {self.user}'

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class Opportunity(models.Model):
    class OpportunityType(models.TextChoices):
        SCHEME = 'scheme', 'Government scheme'
        SCHOLARSHIP = 'scholarship', 'Scholarship'
        INTERNSHIP = 'internship', 'Internship'

    id = models.CharField(primary_key=True, max_length=32)
    opportunity_type = models.CharField(
        db_column='type',
        max_length=20,
        choices=OpportunityType.choices,
    )
    title = models.CharField(max_length=255)
    provider = models.CharField(max_length=255)
    image = models.CharField(max_length=500, blank=True, default='')
    benefit = models.CharField(max_length=255)
    deadline = models.CharField(max_length=100)
    verified = models.CharField(max_length=100, blank=True, default='')
    mode = models.CharField(max_length=100, blank=True, default='')
    min_education = models.CharField(max_length=40, blank=True, default='')
    min_marks = models.FloatField(null=True, blank=True)
    max_income = models.PositiveBigIntegerField(null=True, blank=True)
    category = models.CharField(max_length=40, blank=True, default='')
    gender = models.CharField(max_length=20, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    pwd_only = models.BooleanField(default=False)
    skills = models.TextField(blank=True, default='[]')
    description = models.TextField()
    eligibility = models.TextField(blank=True, default='')
    documents = models.TextField(blank=True, default='')
    official_link = models.CharField(max_length=500)

    class Meta:
        managed = False
        db_table = 'avsar_opportunity'
        ordering = ['title']

    def __str__(self):
        return self.title
