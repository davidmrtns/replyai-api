from pydantic import BaseModel, Field
from typing import Optional


class Discount(BaseModel):
    value: float
    limitDate: Optional[str]
    dueDateLimitDays: int
    type: str


class Fine(BaseModel):
    value: float
    type: str


class Interest(BaseModel):
    value: float
    type: str


class Payment(BaseModel):
    object: str
    id: str
    dateCreated: str
    customer: str
    installment: str
    paymentLink: Optional[str]
    value: float
    netValue: float
    originalValue: Optional[float]
    interestValue: Optional[float]
    description: str
    billingType: str
    canBePaidAfterDueDate: bool
    confirmedDate: str
    pixTransaction: Optional[str]
    status: str
    dueDate: str
    originalDueDate: str
    paymentDate: str
    clientPaymentDate: str
    installmentNumber: int
    invoiceUrl: str
    invoiceNumber: str
    externalReference: Optional[str]
    deleted: bool
    anticipated: bool
    anticipable: bool
    creditDate: str
    estimatedCreditDate: str
    transactionReceiptUrl: str
    nossoNumero: str
    bankSlipUrl: str
    lastInvoiceViewedDate: Optional[str]
    lastBankSlipViewedDate: Optional[str]
    discount: Discount
    fine: Fine
    interest: Interest
    postalService: bool
    custody: Optional[str]
    refunds: Optional[str]


class Taxes(BaseModel):
    retainIss: bool = Field(..., alias="retainIss")
    iss: float
    cofins: float
    csll: float
    inss: float
    ir: float
    pis: float


class Invoice(BaseModel):
    object: str
    id: str
    status: str
    customer: str
    type: str
    statusDescription: Optional[str] = None
    serviceDescription: str
    pdfUrl: Optional[str] = None
    xmlUrl: Optional[str] = None
    rpsSerie: Optional[str] = None
    rpsNumber: Optional[str] = None
    number: Optional[str] = None
    validationCode: Optional[str] = None
    value: float
    deductions: float
    effectiveDate: str
    observations: str
    estimatedTaxesDescription: Optional[str] = ""
    payment: str
    installment: Optional[str] = None
    taxes: Taxes
    municipalServiceCode: str
    municipalServiceName: str


class AsaasPaymentRequest(BaseModel):
    id: str
    event: str
    dateCreated: str
    payment: Payment


class AsaasInvoiceRequest(BaseModel):
    id: str
    event: str
    dateCreated: str
    invoice: Invoice
