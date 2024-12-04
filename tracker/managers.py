from datetime import datetime
from django.db import models


class CampaignsQuerySet(models.QuerySet):
    def get_active(self):
        return self.filter(active=True)

    def get_inactive(self):
        return self.filter(active=False)


class TransactionsQuerySet(models.QuerySet):
    def get_total(self):
        return self.aggregate(total=models.Sum("premium"))["total"] or 0
    
    def get_days_in_trade(self):
        today = datetime.today().date()
        earliest = self.earliest("transaction_date").transaction_date
        delta = today - earliest
        if delta.days:
            return delta.days
        else:
            return 1
    
    def get_annualized_return(self):
        total_profit = self.aggregate(total=models.Sum("premium"))["total"] or 0
        
        if self.filter(type="sell"):
            sell_transaction = self.get(type="sell")
            shares = sell_transaction.contracts
            sell_price = sell_transaction.strike_price
            total_invested = shares * sell_price
            annualized_return = (((total_profit / total_invested) / self.get_days_in_trade()) * 365) * 100
        else:
            latest_transaction = self.latest("transaction_date")
            total_invested = (latest_transaction.contracts * 100) * latest_transaction.strike_price
            annualized_return = (((total_profit / total_invested) / self.get_days_in_trade()) * 365) * 100

        return annualized_return