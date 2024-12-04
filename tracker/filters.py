import django_filters
from tracker.models import Campaign


class CampaignFilter(django_filters.FilterSet):
    CAMPAIGN_STATUS_CHOICES = (
        (False, "Completed"),
        (True, "In-Progress"),
    )
    campaign_status = django_filters.ChoiceFilter(
        choices=CAMPAIGN_STATUS_CHOICES,
        field_name="active",
        label="Campaign Status",
        empty_label="Any",
    )

    class Meta:
        model = Campaign
        fields = ("campaign_status",)
