# Generated by Django 2.2.20 on 2021-07-07 18:40

from django.db import migrations


class Migration(migrations.Migration):

    def move_acts_to_act_model(apps, schema_editor):
        Deal = apps.get_model("planner", "Deal")
        ActOfAcceptance = apps.get_model("planner", "ActOfAcceptance")

        for deal in Deal.objects.all():
            if deal.act_date:
                ActOfAcceptance.objects.create(deal=deal,
                                               number=deal.number,
                                               date=deal.act_date,
                                               value=deal.act_value,
                                               creator_id=2,
                                               )

    def move_payments_to_payment_model(apps, schema_editor):
        Deal = apps.get_model("planner", "Deal")
        Payment = apps.get_model("planner", "Payment")

        for deal in Deal.objects.all():
            pay_date = deal.pay_date or deal.expire_date
            if deal.pay_status == 'AP':
                Payment.objects.create(deal=deal,
                                       date=pay_date,
                                       value=deal.advance,
                                       creator_id=2,
                                       )
            if deal.pay_status == 'PU':
                Payment.objects.create(deal=deal,
                                       date=pay_date,
                                       value=deal.value,
                                       creator_id=2,
                                       )

    dependencies = [
        ('planner', '0033_actofacceptance_payment'),
    ]

    operations = [
        migrations.RunPython(move_acts_to_act_model),
        migrations.RunPython(move_payments_to_payment_model),
    ]
