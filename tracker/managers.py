from django.db import models


class CampaignsQuerySet(models.QuerySet):
    def get_active(self):
        return self.filter(active=True)

    def get_inactive(self):
        return self.filter(active=False)


class TransactionsQuerySet(models.QuerySet):
    def get_total(self):
        return self.aggregate(total=models.Sum("premium"))["total"] or 0
