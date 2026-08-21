from django.forms import ModelForm
from .models import Review, UserGameList


class ReviewForm(ModelForm):
    class Meta:
        model = Review
        fields = ["title", "rating", "body"]


class UserGameListForm(ModelForm):
    class Meta:
        model = UserGameList
        fields = ["status"]
