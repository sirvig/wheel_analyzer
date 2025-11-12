"""Forms for the scanner application."""

from django import forms


class IndividualStockScanForm(forms.Form):
    """Form for scanning individual stock options."""

    ticker = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white",
                "placeholder": "Enter ticker symbol (e.g., AAPL)",
                "autofocus": True,
            }
        ),
    )

    option_type = forms.ChoiceField(
        choices=[
            ("put", "Put Options"),
            ("call", "Call Options"),
        ],
        required=True,
        widget=forms.RadioSelect(
            attrs={
                "class": "w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600",
            }
        ),
    )

    weeks = forms.IntegerField(
        initial=4,
        min_value=1,
        max_value=52,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white",
            }
        ),
    )

    def clean_ticker(self):
        """Validate and normalize ticker symbol."""
        ticker = self.cleaned_data["ticker"].strip().upper()

        # Basic validation: alphanumeric only, 1-10 chars
        if not ticker.isalnum():
            raise forms.ValidationError(
                "Ticker must contain only letters and numbers"
            )

        if len(ticker) < 1 or len(ticker) > 10:
            raise forms.ValidationError("Ticker must be 1-10 characters")

        return ticker
