from django.contrib import admin
from .models import (
    AdminUser,
    AuditLog,
    Coupon,
    Driver,
    Rider,
    Ride,
    SOSAlert,
    SurgeZone,
)

admin.site.register(AdminUser)
admin.site.register(Rider)
admin.site.register(Driver)
admin.site.register(Ride)
admin.site.register(SurgeZone)
admin.site.register(Coupon)
admin.site.register(SOSAlert)
admin.site.register(AuditLog)