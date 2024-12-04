from django.db import models


class OptionsWatchQuerySet(models.QuerySet):
    def get_active(self):
        return self.filter(active=True)

    def get_inactive(self):
        return self.filter(active=False)
