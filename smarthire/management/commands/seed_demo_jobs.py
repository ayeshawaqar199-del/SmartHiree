from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from smarthire.models import Profile, Job

DEMO_JOBS = [
    {
        'title': 'Junior Python Developer', 'company': 'Cedarline Digital (Demo)', 'location': 'Lahore, Pakistan',
        'employment_type': 'Full-time', 'salary_min': 1800000, 'salary_max': 3000000,
        'required_skills': 'Python, Django, MySQL, REST APIs',
        'description': 'Demo listing for SmartHire project demonstration.\n\nHelp build and maintain web applications, work with a supportive engineering team, and contribute to API and database improvements. This sample vacancy is illustrative and is not a real job opening.',
    },
    {
        'title': 'Frontend Developer', 'company': 'Pixel Grove Studio (Demo)', 'location': 'Karachi, Pakistan',
        'employment_type': 'Full-time', 'salary_min': 2000000, 'salary_max': 3600000,
        'required_skills': 'JavaScript, React, HTML, CSS',
        'description': 'Demo listing for SmartHire project demonstration.\n\nCreate accessible, responsive interfaces and collaborate with design and backend teammates to deliver polished product experiences. This sample vacancy is illustrative and is not a real job opening.',
    },
    {
        'title': 'Data Analyst', 'company': 'Meridian Works (Demo)', 'location': 'Islamabad, Pakistan',
        'employment_type': 'Full-time', 'salary_min': 1900000, 'salary_max': 3300000,
        'required_skills': 'SQL, Excel, Python, Data Visualization',
        'description': 'Demo listing for SmartHire project demonstration.\n\nTurn business questions into useful analysis, prepare clear reports, and help teams make decisions using reliable data. This sample vacancy is illustrative and is not a real job opening.',
    },
    {
        'title': 'Product Designer', 'company': 'Northstar Product Lab (Demo)', 'location': 'Lahore, Pakistan',
        'employment_type': 'Full-time', 'salary_min': 2100000, 'salary_max': 3600000,
        'required_skills': 'Figma, UX Research, Prototyping, UI Design',
        'description': 'Demo listing for SmartHire project demonstration.\n\nDesign clear user journeys from research through prototypes, partner with product teams, and help make digital services easier to use. This sample vacancy is illustrative and is not a real job opening.',
    },
    {
        'title': 'Recruitment Coordinator', 'company': 'PeopleSpring (Demo)', 'location': 'Karachi, Pakistan',
        'employment_type': 'Full-time', 'salary_min': 1500000, 'salary_max': 2400000,
        'required_skills': 'Recruitment, Communication, Scheduling, HR',
        'description': 'Demo listing for SmartHire project demonstration.\n\nSupport hiring teams with interview coordination, candidate communication, and organised recruitment records. This sample vacancy is illustrative and is not a real job opening.',
    },
    {
        'title': 'QA Engineer', 'company': 'Blue Oak Software (Demo)', 'location': 'Remote, Pakistan',
        'employment_type': 'Contract', 'salary_min': 1800000, 'salary_max': 3200000,
        'required_skills': 'Software Testing, Selenium, Python, Bug Tracking',
        'description': 'Demo listing for SmartHire project demonstration.\n\nPlan and run practical tests, document issues clearly, and work with developers to improve product quality across web releases. This sample vacancy is illustrative and is not a real job opening.',
    },
]

class Command(BaseCommand):
    help = 'Create an idempotent set of clearly labelled SmartHire sample jobs.'

    @transaction.atomic
    def handle(self, *args, **options):
        employer, created = User.objects.get_or_create(
            username='smarthire_demo_employer',
            defaults={'email':'demo-employer@smarthire.local','first_name':'SmartHire','last_name':'Demo'},
        )
        if created:
            employer.set_unusable_password()
            employer.save(update_fields=['password'])
        Profile.objects.get_or_create(
            user=employer,
            defaults={'role':'employer','company_name':'SmartHire Demo Employers','location':'Pakistan'},
        )
        for row in DEMO_JOBS:
            Job.objects.update_or_create(
                employer=employer,
                title=row['title'],
                defaults={**row,'is_active':True},
            )
        self.stdout.write(self.style.SUCCESS(f'Created or refreshed {len(DEMO_JOBS)} demo job listings.'))
