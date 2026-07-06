from django import forms
from .models import Profile

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "avatar",
            "bio"
        ]



from django.contrib.auth.models import User
from work.models import Profile

for user in User.objects.all():
    Profile.objects.get_or_create(user=user)
print("Profiles created successfully")