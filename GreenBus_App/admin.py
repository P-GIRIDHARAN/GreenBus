from django.contrib import admin

from GreenBus_App.models import UserModel, PaymentModel, TicketModel, BusModel, CompanyModel, RouteModel

# Register your models here.
admin.site.register(UserModel)
admin.site.register(PaymentModel)
admin.site.register(TicketModel)
admin.site.register(BusModel)
admin.site.register(CompanyModel)
admin.site.register(RouteModel)

