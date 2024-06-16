from django import forms
from tracker.models import Account, Campaign, Transaction


class TransactionForm(forms.ModelForm):
    transaction_date = forms.DateField(widget=forms.HiddenInput(), required=False)
    campaign = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_campaign(self):
        data = self.cleaned_data["campaign"]
        # TODO Add error checking here
        campaign = Campaign.objects.get(id=data)
        return campaign

    class Meta:
        model = Transaction
        fields = (
            "type",
            "strike_price",
            "contracts",
            "expiration_date",
            "premium",
            "campaign",
            "transaction_date",
        )
        widgets = {
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
        }


class CampaignForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        queryset=None, widget=forms.Select(), required=True
    )

    user = forms.HiddenInput()
    start_date = forms.HiddenInput()
    active = forms.HiddenInput()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(CampaignForm, self).__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(user=self.user)
        self.fields["user"].initial = self.user

    class Meta:
        model = Campaign
        fields = ("user", "stock", "account", "active", "start_date")
