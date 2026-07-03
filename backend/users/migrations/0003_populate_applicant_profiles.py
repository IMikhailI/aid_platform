from django.db import migrations


def create_missing_applicant_profiles(apps, schema_editor):
    User = apps.get_model("users", "User")
    ApplicantProfile = apps.get_model("users", "ApplicantProfile")
    existing_user_ids = ApplicantProfile.objects.values_list("user_id", flat=True)
    missing_profiles = [
        ApplicantProfile(user_id=user_id)
        for user_id in User.objects.filter(role="applicant")
        .exclude(id__in=existing_user_ids)
        .values_list("id", flat=True)
        .iterator()
    ]
    ApplicantProfile.objects.bulk_create(missing_profiles, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("users", "0002_applicantprofile")]

    operations = [
        migrations.RunPython(create_missing_applicant_profiles, migrations.RunPython.noop),
    ]
