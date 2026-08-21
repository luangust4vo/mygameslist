from django.contrib.auth.mixins import UserPassesTestMixin


class GroupRequiredMixin(UserPassesTestMixin):
    group_required = None

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.group_required is None:
            return False

        groups = self.group_required
        if isinstance(groups, str):
            groups = [groups]
        return user.groups.filter(name__in=groups).exists()
