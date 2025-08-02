"""
Payment domain models for CAPP cross-border payment system
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator, model_validator
from pydantic.types import condecimal


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    ROUTING = "routing"
    SETTLING = "settling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    OFFLINE_QUEUED = "offline_queued"


class PaymentType(str, Enum):
    """Payment type enumeration"""
    PERSONAL_REMITTANCE = "personal_remittance"
    BUSINESS_PAYMENT = "business_payment"
    BULK_DISBURSEMENT = "bulk_disbursement"
    MERCHANT_PAYMENT = "merchant_payment"
    AIRTIME_PURCHASE = "airtime_purchase"
    BILL_PAYMENT = "bill_payment"


class PaymentMethod(str, Enum):
    """Payment method enumeration"""
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    CASH_PICKUP = "cash_pickup"
    DIGITAL_WALLET = "digital_wallet"
    CRYPTO = "crypto"


class MMOProvider(str, Enum):
    """Mobile Money Operator providers"""
    MPESA = "mpesa"
    ORANGE_MONEY = "orange_money"
    MTN_MOBILE_MONEY = "mtn_mobile_money"
    AIRTEL_MONEY = "airtel_money"
    VODAFONE_CASH = "vodafone_cash"
    TIGO_PESA = "tigo_pesa"
    MOOV_MONEY = "moov_money"
    ECOCASH = "ecocash"
    MPESA_TANZANIA = "mpesa_tanzania"
    MPESA_UGANDA = "mpesa_uganda"


class Currency(str, Enum):
    """Supported African currencies"""
    # West Africa
    NGN = "NGN"  # Nigerian Naira
    XOF = "XOF"  # West African CFA Franc
    GHS = "GHS"  # Ghanaian Cedi
    GMD = "GMD"  # Gambian Dalasi
    SLL = "SLL"  # Sierra Leonean Leone
    
    # East Africa
    KES = "KES"  # Kenyan Shilling
    UGX = "UGX"  # Ugandan Shilling
    TZS = "TZS"  # Tanzanian Shilling
    RWF = "RWF"  # Rwandan Franc
    BIF = "BIF"  # Burundian Franc
    ETB = "ETB"  # Ethiopian Birr
    SOS = "SOS"  # Somali Shilling
    
    # Southern Africa
    ZAR = "ZAR"  # South African Rand
    ZMW = "ZMW"  # Zambian Kwacha
    BWP = "BWP"  # Botswana Pula
    SZL = "SZL"  # Eswatini Lilangeni
    LSL = "LSL"  # Lesotho Loti
    MWK = "MWK"  # Malawian Kwacha
    MZN = "MZN"  # Mozambican Metical
    AOA = "AOA"  # Angolan Kwanza
    NAD = "NAD"  # Namibian Dollar
    
    # Central Africa
    XAF = "XAF"  # Central African CFA Franc
    CDF = "CDF"  # Congolese Franc
    XAF_CM = "XAF_CM"  # Cameroon CFA Franc
    XAF_TD = "XAF_TD"  # Chad CFA Franc
    
    # North Africa
    EGP = "EGP"  # Egyptian Pound
    MAD = "MAD"  # Moroccan Dirham
    TND = "TND"  # Tunisian Dinar
    DZD = "DZD"  # Algerian Dinar
    LYD = "LYD"  # Libyan Dinar
    SDG = "SDG"  # Sudanese Pound
    
    # Others
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound


class Country(str, Enum):
    """Supported African countries"""
    # West Africa
    NIGERIA = "NG"
    GHANA = "GH"
    SENEGAL = "SN"
    COTE_DIVOIRE = "CI"
    BURKINA_FASO = "BF"
    MALI = "ML"
    NIGER = "NE"
    TOGO = "TG"
    BENIN = "BJ"
    GUINEA = "GN"
    SIERRA_LEONE = "SL"
    LIBERIA = "LR"
    GAMBIA = "GM"
    GUINEA_BISSAU = "GW"
    CAPE_VERDE = "CV"
    
    # East Africa
    KENYA = "KE"
    UGANDA = "UG"
    TANZANIA = "TZ"
    RWANDA = "RW"
    BURUNDI = "BI"
    ETHIOPIA = "ET"
    SOMALIA = "SO"
    DJIBOUTI = "DJ"
    ERITREA = "ER"
    SOUTH_SUDAN = "SS"
    
    # Southern Africa
    SOUTH_AFRICA = "ZA"
    ZAMBIA = "ZM"
    BOTSWANA = "BW"
    ESWATINI = "SZ"
    LESOTHO = "LS"
    MALAWI = "MW"
    MOZAMBIQUE = "MZ"
    ANGOLA = "AO"
    NAMIBIA = "NA"
    ZIMBABWE = "ZW"
    
    # Central Africa
    CAMEROON = "CM"
    CHAD = "TD"
    CENTRAL_AFRICAN_REPUBLIC = "CF"
    CONGO = "CG"
    DEMOCRATIC_REPUBLIC_CONGO = "CD"
    GABON = "GA"
    EQUATORIAL_GUINEA = "GQ"
    SAO_TOME_PRINCIPE = "ST"
    
    # North Africa
    EGYPT = "EG"
    MOROCCO = "MA"
    TUNISIA = "TN"
    ALGERIA = "DZ"
    LIBYA = "LY"
    SUDAN = "SD"
    MAURITANIA = "MR"


class PaymentRoute(BaseModel):
    """Payment route information"""
    route_id: UUID = Field(default_factory=uuid4)
    from_country: Country
    to_country: Country
    from_currency: Currency
    to_currency: Currency
    from_mmo: Optional[MMOProvider] = None
    to_mmo: Optional[MMOProvider] = None
    from_bank: Optional[str] = None
    to_bank: Optional[str] = None
    exchange_rate: condecimal(max_digits=10, decimal_places=6)
    fees: condecimal(max_digits=10, decimal_places=2)
    estimated_delivery_time: int  # in minutes
    success_rate: float = Field(ge=0.0, le=1.0)
    cost_score: float = Field(ge=0.0, le=1.0)
    speed_score: float = Field(ge=0.0, le=1.0)
    reliability_score: float = Field(ge=0.0, le=1.0)
    total_score: float = Field(ge=0.0, le=1.0)
    
    class Config:
        json_encoders = {
            UUID: str,
            Decimal: str
        }


class PaymentPreferences(BaseModel):
    """Payment preferences for optimization"""
    prioritize_cost: bool = True
    prioritize_speed: bool = False
    prioritize_reliability: bool = False
    max_delivery_time: Optional[int] = None  # in minutes
    max_fees: Optional[Decimal] = None
    preferred_mmo: Optional[MMOProvider] = None
    preferred_bank: Optional[str] = None
    allow_offline_processing: bool = True
    require_instant_confirmation: bool = False


class SenderInfo(BaseModel):
    """Sender information"""
    sender_id: Optional[UUID] = None
    name: str
    phone_number: str
    email: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    country: Country
    city: Optional[str] = None
    address: Optional[str] = None
    kyc_verified: bool = False
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)


class RecipientInfo(BaseModel):
    """Recipient information"""
    recipient_id: Optional[UUID] = None
    name: str
    phone_number: str
    email: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    country: Country
    city: Optional[str] = None
    address: Optional[str] = None
    bank_account: Optional[str] = None
    bank_name: Optional[str] = None
    mmo_account: Optional[str] = None
    mmo_provider: Optional[MMOProvider] = None
    kyc_verified: bool = False
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)


class CrossBorderPayment(BaseModel):
    """Cross-border payment model"""
    payment_id: UUID = Field(default_factory=uuid4)
    reference_id: str = Field(..., min_length=1, max_length=50)
    payment_type: PaymentType
    payment_method: PaymentMethod
    
    # Amount and currency
    amount: condecimal(max_digits=15, decimal_places=2, gt=0)
    from_currency: Currency
    to_currency: Currency
    exchange_rate: Optional[condecimal(max_digits=10, decimal_places=6)] = None
    converted_amount: Optional[condecimal(max_digits=15, decimal_places=2)] = None
    
    # Parties
    sender: SenderInfo
    recipient: RecipientInfo
    
    # Routing
    selected_route: Optional[PaymentRoute] = None
    available_routes: List[PaymentRoute] = []
    preferences: PaymentPreferences = Field(default_factory=PaymentPreferences)
    
    # Status and timing
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Fees and costs
    fees: condecimal(max_digits=10, decimal_places=2) = Decimal('0.00')
    total_cost: condecimal(max_digits=10, decimal_places=2) = Decimal('0.00')
    
    # Processing
    agent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    
    # Compliance and security
    compliance_status: str = "pending"
    fraud_score: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: str = "low"
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    
    # Offline support
    offline_queued: bool = False
    sync_attempts: int = 0
    last_sync_attempt: Optional[datetime] = None
    
    @validator('reference_id')
    def validate_reference_id(cls, v):
        """Validate reference ID format"""
        # Allow alphanumeric characters, hyphens, and underscores
        if not all(c.isalnum() or c in '-_' for c in v):
            raise ValueError('Reference ID must contain only alphanumeric characters, hyphens, and underscores')
        return v.upper()
    
    @validator('amount')
    def validate_amount(cls, v):
        """Validate payment amount"""
        if v <= 0:
            raise ValueError('Amount must be greater than zero')
        return v
    
    @model_validator(mode='after')
    def validate_currencies_and_countries(self):
        """Validate currency and country consistency"""
        # Validate currencies
        if self.from_currency == self.to_currency:
            raise ValueError('From and to currencies must be different')
        
        # Validate countries
        if self.sender and self.recipient and self.sender.country == self.recipient.country:
            raise ValueError('Sender and recipient must be in different countries')
        
        return self
    
    def calculate_total_cost(self) -> Decimal:
        """Calculate total cost including fees"""
        return self.amount + self.fees
    
    def is_expired(self) -> bool:
        """Check if payment has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def can_be_cancelled(self) -> bool:
        """Check if payment can be cancelled"""
        return self.status in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]
    
    def update_status(self, new_status: PaymentStatus) -> None:
        """Update payment status"""
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
        
        if new_status == PaymentStatus.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)
    
    class Config:
        json_encoders = {
            UUID: str,
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class PaymentResult(BaseModel):
    """Payment processing result"""
    success: bool
    payment_id: UUID
    status: PaymentStatus
    message: str
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    transaction_hash: Optional[str] = None
    estimated_delivery_time: Optional[int] = None
    fees_charged: Optional[Decimal] = None
    exchange_rate_used: Optional[Decimal] = None
    
    class Config:
        json_encoders = {
            UUID: str,
            Decimal: str
        }


class PaymentBatch(BaseModel):
    """Batch payment model for bulk operations"""
    batch_id: UUID = Field(default_factory=uuid4)
    payments: List[CrossBorderPayment]
    total_amount: Decimal
    total_fees: Decimal
    currency: Currency
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            UUID: str,
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class PaymentAnalytics(BaseModel):
    """Payment analytics data"""
    total_volume: Decimal
    total_count: int
    success_rate: float
    average_fees: Decimal
    average_delivery_time: int  # in minutes
    currency_distribution: Dict[Currency, int]
    country_distribution: Dict[Country, int]
    mmo_distribution: Dict[MMOProvider, int]
    time_period: str  # daily, weekly, monthly, yearly
    start_date: datetime
    end_date: datetime
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        } 