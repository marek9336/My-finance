from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VehicleType(str, Enum):
    car = "car"
    motorcycle = "motorcycle"
    other = "other"


class ServiceRuleUnit(str, Enum):
    days = "days"
    months = "months"
    km = "km"


class PropertyType(str, Enum):
    house = "house"
    apartment = "apartment"
    land = "land"
    other = "other"


class InsuranceType(str, Enum):
    vehicle = "vehicle"
    property = "property"
    household = "household"
    liability = "liability"
    life = "life"
    other = "other"


class NotificationChannel(str, Enum):
    in_app = "in_app"
    email = "email"
    google_calendar = "google_calendar"


class ReminderSource(str, Enum):
    manual = "manual"
    service_rule = "service_rule"
    insurance = "insurance"
    tax = "tax"
    recurring_payment = "recurring_payment"


class ApiErrorDetail(BaseModel):
    field: str
    message: str


class ApiErrorPayload(BaseModel):
    code: str
    message: str
    details: list[ApiErrorDetail] = Field(default_factory=list)


class ApiErrorResponse(BaseModel):
    error: ApiErrorPayload


class VehicleCreate(BaseModel):
    type: VehicleType
    label: str = Field(min_length=1, max_length=200)
    vin: Optional[str] = None
    plateNumber: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    productionYear: Optional[int] = Field(default=None, ge=1886, le=2100)
    purchasedAt: Optional[date] = None
    currentOdometerKm: int = Field(default=0, ge=0)
    notes: Optional[str] = None


class VehicleResponse(BaseModel):
    id: UUID
    type: VehicleType
    label: str
    currentOdometerKm: int
    createdAt: datetime


class VehicleServiceCreate(BaseModel):
    serviceType: str = Field(min_length=1, max_length=100)
    serviceAt: date
    odometerKm: Optional[int] = Field(default=None, ge=0)
    totalCost: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = None
    vendor: Optional[str] = None
    description: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up


class VehicleServiceResponse(BaseModel):
    id: UUID
    vehicleId: UUID
    serviceType: str
    serviceAt: date
    odometerKm: Optional[int]


class VehicleServiceRuleCreate(BaseModel):
    serviceType: str = Field(min_length=1, max_length=100)
    intervalValue: int = Field(gt=0)
    intervalUnit: ServiceRuleUnit
    leadDays: int = Field(default=14, ge=0)


class VehicleServiceRuleResponse(BaseModel):
    id: UUID
    vehicleId: UUID
    serviceType: str
    nextDueDate: Optional[date]
    isActive: bool


class PropertyCreate(BaseModel):
    type: PropertyType
    name: str = Field(min_length=1, max_length=200)
    addressLine1: Optional[str] = None
    city: Optional[str] = None
    postalCode: Optional[str] = None
    countryCode: str = "CZ"
    acquiredAt: Optional[date] = None
    purchasePrice: Optional[Decimal] = Field(default=None, ge=0)
    purchaseCurrency: Optional[str] = None
    estimatedValue: Optional[Decimal] = Field(default=None, ge=0)
    estimatedValueCurrency: Optional[str] = None
    estimatedValueUpdatedAt: Optional[date] = None

    @field_validator("countryCode")
    @classmethod
    def validate_country(cls, value: str) -> str:
        up = value.upper()
        if len(up) != 2:
            raise ValueError("must be 2-letter country code")
        return up

    @field_validator("purchaseCurrency", "estimatedValueCurrency")
    @classmethod
    def validate_currency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up


class PropertyResponse(BaseModel):
    id: UUID
    type: PropertyType
    name: str
    estimatedValue: Optional[Decimal]


class PropertyCostCreate(BaseModel):
    costType: str = Field(min_length=1, max_length=100)
    periodStart: date
    periodEnd: date
    amount: Decimal = Field(ge=0)
    currency: str
    provider: Optional[str] = None
    meterValue: Optional[Decimal] = Field(default=None, ge=0)
    meterUnit: Optional[str] = None
    isRecurring: bool = False

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up

    @model_validator(mode="after")
    def validate_period(self) -> "PropertyCostCreate":
        if self.periodEnd < self.periodStart:
            raise ValueError("periodEnd must be >= periodStart")
        return self


class PropertyCostResponse(BaseModel):
    id: UUID
    propertyId: UUID
    costType: str
    amount: Decimal
    currency: str


class InsuranceCreate(BaseModel):
    insuranceType: InsuranceType
    provider: str = Field(min_length=1, max_length=200)
    policyNumber: Optional[str] = None
    subjectVehicleId: Optional[UUID] = None
    subjectPropertyId: Optional[UUID] = None
    coverageAmount: Optional[Decimal] = Field(default=None, ge=0)
    coverageCurrency: Optional[str] = None
    deductibleAmount: Optional[Decimal] = Field(default=None, ge=0)
    deductibleCurrency: Optional[str] = None
    validFrom: Optional[date] = None
    validTo: Optional[date] = None
    paymentFrequency: Optional[str] = None

    @field_validator("coverageCurrency", "deductibleCurrency")
    @classmethod
    def validate_currency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up

    @model_validator(mode="after")
    def validate_subject(self) -> "InsuranceCreate":
        if self.insuranceType == InsuranceType.vehicle and not self.subjectVehicleId:
            raise ValueError("insuranceType=vehicle requires subjectVehicleId")
        if self.insuranceType in {InsuranceType.property, InsuranceType.household} and not self.subjectPropertyId:
            raise ValueError("insuranceType=property|household requires subjectPropertyId")
        if self.validFrom and self.validTo and self.validTo < self.validFrom:
            raise ValueError("validTo must be >= validFrom")
        return self


class InsuranceResponse(BaseModel):
    id: UUID
    insuranceType: InsuranceType
    provider: str
    validTo: Optional[date]
    isActive: bool


class InsurancePremiumCreate(BaseModel):
    periodStart: date
    periodEnd: date
    amount: Decimal = Field(ge=0)
    currency: str
    paidAt: Optional[date] = None
    paymentTransactionId: Optional[UUID] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up

    @model_validator(mode="after")
    def validate_period(self) -> "InsurancePremiumCreate":
        if self.periodEnd < self.periodStart:
            raise ValueError("periodEnd must be >= periodStart")
        return self


class InsurancePremiumResponse(BaseModel):
    id: UUID
    insuranceId: UUID
    amount: Decimal
    currency: str


class GoogleCalendarConnectRequest(BaseModel):
    authorizationCode: str = Field(min_length=1)
    externalCalendarId: str = Field(min_length=1)


class GoogleCalendarConnectResponse(BaseModel):
    integrationId: UUID
    provider: str
    externalCalendarId: str
    syncEnabled: bool


class NotificationRuleCreate(BaseModel):
    source: ReminderSource
    sourceEntityId: UUID
    titleTemplate: str = Field(min_length=1)
    messageTemplate: Optional[str] = None
    dueAt: datetime
    leadDays: int = Field(default=7, ge=0)
    channel: NotificationChannel
    timezone: str = "Europe/Prague"
    isActive: bool = True


class NotificationRuleResponse(BaseModel):
    id: UUID
    channel: NotificationChannel
    dueAt: datetime
    isActive: bool


class GoogleCalendarSyncRunRequest(BaseModel):
    dryRun: bool = False


class GoogleCalendarSyncRunResponse(BaseModel):
    created: int
    updated: int
    unchanged: int
    canceled: int
    failed: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str


class AppSettings(BaseModel):
    defaultLocale: str = "en"
    defaultTimezone: str = "Europe/Prague"
    calendarProvider: str = "google"
    calendarSyncEnabled: bool = True
    selfRegistrationEnabled: bool = True
    smtpEnabled: bool = False
    autoBackupEnabled: bool = False
    autoBackupIntervalMinutes: int = Field(default=1440, ge=5)
    autoBackupRetentionDays: int = Field(default=30, ge=1)
    autoBackupLastRunAt: Optional[datetime] = None
    sessionTimeoutMinutes: Optional[int] = Field(default=None, ge=1)


class AppSettingsUpdate(BaseModel):
    defaultLocale: Optional[str] = None
    defaultTimezone: Optional[str] = None
    calendarProvider: Optional[str] = None
    calendarSyncEnabled: Optional[bool] = None
    selfRegistrationEnabled: Optional[bool] = None
    smtpEnabled: Optional[bool] = None
    autoBackupEnabled: Optional[bool] = None
    autoBackupIntervalMinutes: Optional[int] = Field(default=None, ge=5)
    autoBackupRetentionDays: Optional[int] = Field(default=None, ge=1)
    autoBackupLastRunAt: Optional[datetime] = None
    sessionTimeoutMinutes: Optional[int] = Field(default=None, ge=1)


class LocaleListResponse(BaseModel):
    locales: list[str]


class LocaleBundleResponse(BaseModel):
    locale: str
    messages: dict[str, str]


class LocalePublishResponse(BaseModel):
    locale: str
    path: str
    keys: int


class BackupImportResponse(BaseModel):
    replaced: bool
    counts: dict[str, int]


class BackupRunResponse(BaseModel):
    created: bool
    file: str
    timestamp: datetime


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    fullName: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        v = value.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email format")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    rememberMe: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthResponse(BaseModel):
    token: str
    userId: UUID
    email: str
    fullName: Optional[str] = None


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    accountType: str = Field(default="checking", min_length=1, max_length=50)
    currency: str = Field(default="CZK")
    initialBalance: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up


class AccountResponse(BaseModel):
    id: UUID
    name: str
    accountType: str
    currency: str
    currentBalance: Decimal
    createdAt: datetime


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    accountType: Optional[str] = Field(default=None, min_length=1, max_length=50)
    currency: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up


class TransactionCreate(BaseModel):
    accountId: UUID
    direction: str = Field(default="expense")
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str
    occurredAt: datetime
    category: Optional[str] = None
    note: Optional[str] = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        v = value.lower().strip()
        if v not in {"income", "expense"}:
            raise ValueError("direction must be income or expense")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up


class TransactionResponse(BaseModel):
    id: UUID
    accountId: UUID
    direction: str
    amount: Decimal
    currency: str
    occurredAt: datetime
    category: Optional[str] = None
    note: Optional[str] = None


class TransactionUpdate(BaseModel):
    direction: Optional[str] = None
    amount: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    currency: Optional[str] = None
    category: Optional[str] = None
    note: Optional[str] = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        v = value.lower().strip()
        if v not in {"income", "expense"}:
            raise ValueError("direction must be income or expense")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        up = value.upper()
        if len(up) != 3:
            raise ValueError("must be 3-letter ISO code")
        return up
