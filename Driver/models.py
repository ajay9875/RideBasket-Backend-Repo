import uuid
from django.db import models


def generate_uuid():
    return str(uuid.uuid4())


# 1. Admin Users & Staff Roles
class AdminUser(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'Super Admin', 'Super Admin'
        OPERATIONS_MANAGER = 'Operations Manager', 'Operations Manager'
        SUPPORT_LEAD = 'Support Lead', 'Support Lead'
        FINANCE_ADMIN = 'Finance Admin', 'Finance Admin'

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        INACTIVE = 'Inactive', 'Inactive'

    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True, db_index=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(
        max_length=30, choices=Role.choices, default=Role.OPERATIONS_MANAGER
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_users'

    def __str__(self):
        return f'{self.name} ({self.role})'

# 2. Riders Table
class Rider(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        BLOCKED = 'Blocked', 'Blocked'
        PENDING = 'Pending', 'Pending'

    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    full_name = models.CharField(max_length=100)
    # ✅ CHANGE THIS LINE - Add null=True, blank=True
    email = models.EmailField(max_length=150, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    wallet_balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # ✅ ADD OTP FIELDS (if not already present)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'riders'

    def __str__(self):
        return self.full_name

# 3. Drivers Table
class Driver(models.Model):
    class VehicleCategory(models.TextChoices):
        BIKE = 'Bike', 'Bike'
        AUTO = 'Auto', 'Auto'
        SEDAN = 'Sedan', 'Sedan'
        SUV = 'SUV', 'SUV'
        EV = 'EV', 'EV'

    class KYCStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        APPROVED = 'Approved', 'Approved'
        REJECTED = 'Rejected', 'Rejected'

    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    
    # Required fields
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Make email nullable (for temporary drivers)
    email = models.EmailField(max_length=150, unique=True, null=True, blank=True)
    
    # OTP Fields
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    # Vehicle Details
    vehicle_category = models.CharField(
        max_length=20, choices=VehicleCategory.choices, null=True, blank=True
    )
    vehicle_model = models.CharField(max_length=100, null=True, blank=True)
    vehicle_number = models.CharField(max_length=50, unique=True, db_index=True, null=True, blank=True)
    
    # ✅ NEW: Registration Certificate (RC)
    registration_certificate = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Vehicle Registration Certificate (RC) Number"
    )
    
    # ✅ NEW: RC document image/upload (if you need to store the file)
    registration_certificate_image = models.ImageField(
        upload_to='driver_documents/rc/',
        null=True,
        blank=True,
        help_text="Upload Registration Certificate image"
    )
    
    kyc_status = models.CharField(
        max_length=20, choices=KYCStatus.choices, default=KYCStatus.PENDING
    )

    is_online = models.BooleanField(default=False, db_index=True)
    wallet_balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )

    total_earnings = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )

    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    current_lat = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True
    )

    current_lng = models.DecimalField(
        max_digits=11, decimal_places=8, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'drivers'
        indexes = [
            models.Index(fields=['is_online', 'kyc_status']),
            models.Index(fields=['registration_certificate']),  # ✅ Index for RC
        ]

    def __str__(self):
        return f'{self.full_name} ({self.vehicle_number or "No Vehicle"})'
    

# 4. Vehicle Documents
class VehicleDocument(models.Model):
    class DocumentType(models.TextChoices):
        LICENSE = 'LICENSE', 'Driving License'
        REGISTRATION = 'REGISTRATION', 'Vehicle Registration (RC)'
        INSURANCE = 'INSURANCE', 'Vehicle Insurance'
        PERMIT = 'PERMIT', 'Commercial Permit'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name='documents'
    )
    document_type = models.CharField(
        max_length=50, choices=DocumentType.choices
    )
    document_number = models.CharField(max_length=100, blank=True, null=True)
    document_image = models.ImageField(
        upload_to='vehicle_docs/', blank=True, null=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    expiry_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vehicle_documents'

    def __str__(self):
        return f'{self.driver.full_name} - {self.document_type}'


# 5. Rides Table
class Ride(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        ACCEPTED = 'accepted', 'Accepted'
        DRIVER_ENROUTE = 'driver_enroute', 'Driver Enroute'
        ARRIVED = 'arrived', 'Arrived'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        CASH = 'Cash', 'Cash'
        UPI = 'UPI', 'UPI'
        WALLET = 'Wallet', 'Wallet'
        CARD = 'Card', 'Card'

    class PaymentStatus(models.TextChoices):
        PAID = 'Paid', 'Paid'
        PENDING = 'Pending', 'Pending'
        REFUNDED = 'Refunded', 'Refunded'

    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    booking_code = models.CharField(max_length=20, unique=True, db_index=True)
    rider = models.ForeignKey(
        Rider, on_delete=models.CASCADE, related_name='rides'
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rides',
    )
    vehicle_category = models.CharField(max_length=30)
    pickup_address = models.TextField()
    pickup_lat = models.DecimalField(max_digits=10, decimal_places=8)
    pickup_lng = models.DecimalField(max_digits=11, decimal_places=8)
    dropoff_address = models.TextField()
    dropoff_lat = models.DecimalField(max_digits=10, decimal_places=8)
    dropoff_lng = models.DecimalField(max_digits=11, decimal_places=8)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.REQUESTED, db_index=True
    )
    distance_km = models.DecimalField(max_digits=6, decimal_places=2)
    fare_amount = models.DecimalField(max_digits=10, decimal_places=2)
    surge_multiplier = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.00
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.UPI,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    otp_code = models.CharField(max_length=6, default='1234')
    sos_triggered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ ADD THESE OTP FIELDS
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'rides'
        indexes = [
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['rider', 'status']),
        ]

    def __str__(self):
        return f'Ride #{self.booking_code} - {self.status}'


# 6. Earnings Transactions
class EarningsTransaction(models.Model):
    class TransactionType(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit'
        PAYOUT = 'PAYOUT', 'Payout'

    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name='earnings_transactions'
    )
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(
        max_length=20, choices=TransactionType.choices
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'earnings_transactions'

    def __str__(self):
        return f'{self.driver.full_name} - {self.amount} ({self.transaction_type})'


# 7. App Notifications
class AppNotification(models.Model):
    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_notifications'

    def __str__(self):
        return f'{self.driver.full_name} - {self.title}'


# 8. Chat Messages
class ChatMessage(models.Model):
    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    ride = models.ForeignKey(
        Ride, on_delete=models.CASCADE, related_name='chat_messages'
    )
    sender_type = models.CharField(max_length=20, default='DRIVER')
    message_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'

    def __str__(self):
        return f'Message on {self.ride.booking_code}'


# 9. Surge Zones
class SurgeZone(models.Model):
    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    zone_name = models.CharField(max_length=100)
    center_lat = models.DecimalField(max_digits=10, decimal_places=8)
    center_lng = models.DecimalField(max_digits=11, decimal_places=8)
    radius_km = models.DecimalField(max_digits=5, decimal_places=2)
    multiplier = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.00
    )
    auto_surge = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'surge_zones'

    def __str__(self):
        return f'{self.zone_name} ({self.multiplier}x)'


# 10. Coupons
class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'Percentage', 'Percentage'
        FLAT = 'Flat', 'Flat'

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        EXPIRED = 'Expired', 'Expired'
        DISABLED = 'Disabled', 'Disabled'

    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_type = models.CharField(
        max_length=20, choices=DiscountType.choices
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2)
    min_fare = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    usage_count = models.IntegerField(default=0)
    max_usage_limit = models.IntegerField(default=1000)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    expiry_date = models.DateField()

    class Meta:
        db_table = 'coupons'

    def __str__(self):
        return self.code


# 11. SOS Alerts Log
class SOSAlert(models.Model):
    class Status(models.TextChoices):
        ACTIVE_EMERGENCY = 'ACTIVE_EMERGENCY', 'Active Emergency'
        DISPATCHED = 'DISPATCHED', 'Dispatched'
        RESOLVED_FALSE_ALARM = (
            'RESOLVED_FALSE_ALARM',
            'Resolved (False Alarm)',
        )
        RESOLVED_POLICE_NOTIFIED = (
            'RESOLVED_POLICE_NOTIFIED',
            'Resolved (Police Notified)',
        )

    id = models.CharField(primary_key=True, max_length=50, default=generate_uuid)
    ride = models.ForeignKey(
        Ride, on_delete=models.CASCADE, related_name='sos_alerts'
    )
    alert_code = models.CharField(max_length=100, db_index=True)
    rider_name = models.CharField(max_length=100)
    driver_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE_EMERGENCY,
    )
    triggered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sos_alerts'

    def __str__(self):
        return f'SOS: {self.alert_code} - {self.status}'


# 12. Audit Logs
class AuditLog(models.Model):
    admin_name = models.CharField(max_length=100)
    admin_email = models.EmailField(max_length=150)
    action = models.CharField(max_length=100)
    module = models.CharField(max_length=50)
    details = models.TextField()
    ip_address = models.CharField(max_length=45)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'

    def __str__(self):
        return f'{self.admin_name} - {self.action} ({self.created_at})'