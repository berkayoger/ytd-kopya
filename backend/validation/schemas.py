from pydantic import BaseModel, EmailStr, Field


class LoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class CreateOrderSchema(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    amount: float = Field(gt=0)
