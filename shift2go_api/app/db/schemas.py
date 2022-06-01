from os import name
import typing as t
from datetime import datetime

from pydantic import BaseModel
from pydantic.types import NoneBytes


class TokenData(BaseModel):
    email: str = None
    permissions: str = "user"


class PasswordChange(BaseModel):
    user_id: int
    email: str
    old_password: str
    new_password: str


class TokenPasswordChange(BaseModel):
    token: str
    new_password: str


class PasswordReset(BaseModel):
    email: str


class UserRegister(BaseModel):
    email: str
    password: str
    firstname: str = None
    lastname: str = None
    address: str
    phone: str
    countryCode: str = None

    class Config:
        orm_mode = True


class AdminRegister(BaseModel):
    email: str
    password: str


class UserEditBase(BaseModel):
    firstname: str = None
    lastname: str = None
    phone: str = None
    profilePicture: str = None
    address: str = None
    deviceTokens: t.List[str] = None
    latitude: float = None
    longitude: float = None
    countryCode: str = None


class AdminEdit(UserEditBase):
    profilePicture: str = None


class AdminOut(BaseModel):
    id: int
    userID: int
    profilePicture: str = None
    rating: float = None
    createdAt: datetime = None
    udatedAt: datetime = None
    owner: t.Any = None

    class Config:
        orm_mode = True


class AdminOutToken(BaseModel):
    admin: AdminOut
    access_token: str


class HotelAdminRegister(UserRegister):
    email: str
    password: str
    address: str
    profilePicture: t.Optional[str] = None

    class Config:
        orm_mode = True


class HotelAdminEdit(UserEditBase):
    profilePicture: str = None


class HotelAdminOut(BaseModel):
    id: int
    userID: int
    profilePicture: str = None
    rating: float = None
    createdAt: datetime = None
    updatedAt: datetime = None
    owner: t.Any = None
    hotels: t.Any = None
    notification: t.Any = {
        'email': True,
        'push': True
    }

    class Config:
        orm_mode = True


class HotelAdminToken(BaseModel):
    manager: HotelAdminOut
    access_token: str


class ContractorEdit(UserEditBase):
    profilePicture: str = None
    # rating: float = None
    # badges: t.List[int] = None
    jobRoles: t.List[int] = None
    certificates: t.List[int] = None


class ContractorOut(BaseModel):
    id: int
    userID: int
    profilePicture: str = None
    rating: float = None
    completedShiftsCount: int = None
    verified: bool = None
    createdAt: datetime = None
    updatedAt: datetime = None
    owner: t.Any = None
    bank: t.Any = None
    certificates: t.Any = None
    roles: t.Any = None
    reviews: t.Any = None
    documents: t.Any = None
    badge_count: int = None
    # jobRoles: t.List[int] = None
    # certificates: t.Any = None
    # verificationDocuments: t.Any = None

    class Config:
        orm_mode = True


class RequestVerification(BaseModel):
    email: str


class ManagerOut(BaseModel):
    id: int
    userID: int
    profilePicture: str = None
    rating: float = None
    createdAt: datetime = None
    udatedAt: datetime = None
    owner: t.Any = None
    hotels: t.Any = None


class UserBase(BaseModel):
    email: str
    firstname: str = None
    lastname: str = None
    is_superuser: bool = False
    is_verified: bool = False


class UserDetails(UserBase):
    id: int = None
    phone: str = None
    email: str = None
    profilePicture: str = None
    userType: str = None
    address: str = None
    deviceTokens: t.List[str] = None
    manager: t.Any = None
    contractor: t.Any = None
    admin: t.Any = None

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserDetails = None

    class Config:
        orm_mode = True


class BankEdit(BaseModel):
    name: str = None
    accountNumber: str = None
    routingNumber: str = None


class BankIn(BaseModel):
    name: str
    accountNumber: str
    routingNumber: str = None


class BankOut(BaseModel):
    id: int
    name: str = None
    createdBy: int
    accountNumber: str
    routingNumber: str = None
    createdAt: datetime = None
    updatedAt: datetime = None
    owner: t.Any = None

    class Config:
        orm_mode = True


class BadgeEdit(BaseModel):
    name: str = None
    image: str = None


class BadgeIn(BaseModel):
    name: str
    image: str
    type: str = 'HOTEL or USER'


class BadgeOut(BaseModel):
    id: int = None
    name: str = None
    image: str = None
    type: str = None
    createdBy: int = None
    createdAt: datetime = None
    updatedAt: datetime = None

    class Config:
        orm_mode = True


class NotificationSettingsAll(BaseModel):
    push: bool
    email: bool


class NotificationSettingsIn(BaseModel):
    push: bool = True
    email: bool = True
    cancels_shift: bool = True
    ends_shift: bool = True
    begins_shift: bool = True
    accepts_shift: bool = True
    declines_shift: bool = True


class HotelIn(BaseModel):
    legal_name: str
    phone: str
    address: str
    employerIdentificationNumber: str = None
    # bank_id: int = None
    pictures: t.List[str] = None
    contractorsRadius: int = 20
    notification: NotificationSettingsAll
    longitude: float
    latitude: float
    bank: BankIn


class HotelOut(BaseModel):
    id: int
    name: str
    phone: str
    address: str = None
    employerIdentificationNumber: str = None
    bank_id: int = None
    pictures: t.List[str] = None
    favouriteContractors: t.List[int] = None
    contractorsRadius: int = None
    rating: float = None
    longitude: float = 0
    latitude: float = 0
    createdAt: datetime = None
    updatedAt: datetime = None
    owner: t.Any = None
    manager: t.Any = None
    bank: t.Any = None
    favourites: t.Any = None
    notification: dict = {
        'email': True,
        'push': True
    }

    class Config:
        orm_mode = True


class HotelEdit(BaseModel):
    name: str = None
    phone: str = None
    address: str = None
    employerIdentificationNumber: str = None
    # bank_id: int = None
    pictures: t.List[str] = None
    # favouriteContractors: t.List[int] = None
    longitude: float = None
    latitude: float = None
    contractorsRadius: int = None
    notification: NotificationSettingsIn = None
    bank: BankEdit = None


class CertificateIn(BaseModel):
    url: str
    certificate_type_id: int


class CertificateOut(CertificateIn):
    id: int
    url: str
    certificate_type_id: int
    createdBy: int
    createdAt: datetime = None
    updatedAt: datetime = None
    owner: t.Any = None
    type: t.Any = None

    class Config:
        orm_mode = True


class CertificateEdit(BaseModel):
    url: str = None


class JobRolesIn(BaseModel):
    name: str
    image: str


class JobRolesOut(JobRolesIn):
    id: int
    name: str
    image: str
    createdBy: int
    createdAt: datetime = None
    updatedAt: datetime = None
    owner: t.Any = None

    class Config:
        orm_mode = True


class JobRolesEdit(BaseModel):
    name: str
    image: str = None


class ReviewsIn(BaseModel):
    shift_id: int
    # reviewee_id: int
    reviewee_type: str = 'HOTEL or USER'
    comment: str = None
    rating: float
    badge_id: int = None


class ReviewsEdit(BaseModel):
    comment: str
    rating: float
    # badge_id: int


class ReviewsOut(BaseModel):
    id: int = None
    shift_id: int = None
    reviewee_id: int = None
    reviewee_type: str = None
    reviewer: int = None
    comment: str = None
    rating: float = None
    badge_id: int = None
    createdAt: datetime = None
    updatedAt: datetime = None
    shift: t.Any = None
    owner: t.Any = None
    badge: t.Any = None

    class Config:
        orm_model = True


class ContractorIn(BaseModel):
    email: str
    password: str
    firstname: str
    lastname: str
    latitude: float = None
    longitude: float = None
    address: str = None
    phone: str = None
    countryCode: str = None
    profilePicture: str = None
    phone: t.Optional[str] = None
    bank: BankIn = None
    jobRoles: t.List[int] = None
    deviceTokens: t.List[str] = None

    class Config:
        orm_mode = True


class ShiftIn(BaseModel):
    name: str
    hotel_id: int
    roles_ids: t.List[int]
    pay: float
    startTime: datetime
    endTime: datetime
    instructions: str = None
    requiredCertificates: t.List[int] = None
    targetAudience: t.List[int] = None
    audienceType: str
    contractor_id: int = None


class ShiftOut(BaseModel):
    id: int
    name: str
    hotel_id: int
    # roles_ids: t.List[int]
    pay: float
    startTime: datetime = None
    endTime: datetime = None
    startedAt: datetime = None
    endedAt: datetime = None
    instructions: str = None
    # requiredCertificates: t.List[int]
    targetAudience: t.List[int] = None
    audienceType: str
    active: bool
    clockInLatitude: float = None
    clockOutLatitude: float = None
    clockInLongitude: float = None
    clockOutLongitude: float = None
    status: str
    confirmed: bool
    contractor_id: int = None
    createdAt: datetime = None
    createdBy: int = None
    updatedAt: datetime = None
    contractor: t.Any = None
    hotel: t.Any = None
    manager: t.Any = None
    roles: t.Any = None
    requests: t.Any = None
    owner: t.Any = None
    certificates_types: t.Any = None

    class Config:
        orm_mode = True


class ShiftEdit(BaseModel):
    name: str = None
    roles_ids: t.List[int] = None
    pay: float = None
    instructions: str = None
    requiredCertificatesTypes: t.List[int] = None
    targetAudience: t.List[int] = None
    # audienceType: str = None
    # clockInLatitude: float = None
    # clockOutLatitude: float = None
    # clockInLongitude: float = None
    # clockOutLongitude: float = None
    # status: str = None
    active: bool = None
    startTime: datetime = None
    endTime: datetime = None


class CancellationIn(BaseModel):
    shift_id: int
    reason: str = None


class CancellationEdit(BaseModel):
    reason: str


class CancellationOut(BaseModel):
    id: int
    reason: str
    shift_id: int
    cancelledBy: int
    owner: t.Any = None
    shift: t.Any = None
    createdAt: datetime = None
    updatedAt: datetime = None

    class Config:
        orm_mode = True


class BillingIn(BaseModel):
    shift_id: int
    hotel_id: int
    status: str = 'PENDING, PAID'
    paymentTransactionID: str = None
    amountPayableToShift2go: float
    amountPayableToContractor: float


class BillingEdit(BaseModel):
    paymentTransactionID: str = None
    status: str = 'PENDING, PAID'


class BillingOut(BaseModel):
    id: int
    shift_id: int
    hotel_id: int
    status: str
    paymentTransactionID: str = None
    owner: t.Any = None
    hotel: t.Any = None
    shift: t.Any = None
    amountPayableToShift2go: float = None
    amountPayableToContractor: float = None
    createdAt: datetime = None
    updatedAt: datetime = None
    createdBy: int

    class Config:
        orm_mode = True


class NotificationIn(BaseModel):
    title: str
    message: str
    notificationType: str = 'BOTH or PUSH or EMAIL'
    receivers: t.List[int]


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    receivers: t.List[int] = None
    createdBy: int
    readBy: t.List[int] = None
    sender: t.Any
    notificationType: str = None
    createdAt: datetime = None
    updatedAt: datetime = None

    class Config:
        orm_mode = True


class CountryIn(BaseModel):
    code: str
    name: str


class CountryOut(CountryIn):
    pass

    class Config:
        orm_mode = True


class CountryEdit(BaseModel):
    name: str


class DocumentsIn(BaseModel):
    url: str


class DocumentsOut(BaseModel):
    id: int
    url: str
    verified: bool
    createdBy: int
    owner: t.Any = None
    createdAt: datetime = None
    updatedAt: datetime = None

    class Config:
        orm_mode = True


class DocumentsEdit(BaseModel):
    url: str = None
    verified: bool = None


class ShiftRequestEdit(BaseModel):
    notes: str = None


class ShiftRequestIn(BaseModel):
    notes: str = None
    shift_id: int


class ShiftRequestOut(BaseModel):
    id: int
    notes: str = None
    shift_id: int
    createdBy: int
    owner: t.Any = None
    shift: t.Any = None
    contractor: t.Any = None
    createdAt: datetime = None
    updatedAt: datetime = None

    class Config:
        orm_mode = True


class NotificationSettingsEdit(NotificationSettingsIn):
    pass


class NotificationSettingsOut(BaseModel):
    id: int
    push: bool
    email: bool
    reminder: int = None
    cancels_shift: bool = None
    ends_shift: bool = None
    begins_shift: bool = None
    accepts_shift: bool = None
    declines_shift: bool = None
    updatedAt: datetime = None
    owner: t.Any = None

    class Config:
        orm_mode = True


class ClockIn(BaseModel):
    shift_id: int
    clockInLatitude: float
    clockInLongitude: float


class ClockOut(BaseModel):
    shift_id: int
    clockOutLatitude: float
    clockOutLongitude: float
    # paymentTransactionID: str
    # amountPayableToShift2go: float
    # amountPayableToContractor: float


class CertificateTypeIn(BaseModel):
    name: str


class CertificateTypeOut(CertificateTypeIn):
    id: int
    createdAt: datetime = None
    updatedAt: datetime = None

    class Config:
        orm_mode = True


# class CertificateTypeEdit(CertificateTypeIn):
#     id: int
#
#     class Config:
#         orm_mode = True

class CertificateTypeEdit(BaseModel):
    id: int
    name: str


class AwardShift(BaseModel):
    contractor_id: int
    shift_id: int


class Hours(BaseModel):
    hours: int


class Penalty(BaseModel):
    existing: int
    deadline: datetime
    message: str


class Summary(BaseModel):
    contractors: int
    hotels: int
    shifts: int
    shifts_completed: int
