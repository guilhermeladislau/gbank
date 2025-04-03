from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional

class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    cpf: str = Field(..., min_length=11, max_length=11, pattern=r'^\d+$')
    senha: str = Field(..., min_length=6)

    class Config:

        json_schema_extra = {
            "example": {
                "nome": "Fulano da Silva",
                "cpf": "12345678900",
                "senha": "senha123"
            }
        }

class LoginRequest(BaseModel):
    cpf: str = Field(..., min_length=11, max_length=11, pattern=r'^\d+$')
    senha: str = Field(..., min_length=6)
  
    class Config:
        json_schema_extra = {
            "example": {
                "cpf": "12345678900",
                "senha": "senha123",
            }
        }

class DepositoRequest(BaseModel):
    cpf_destino: str = Field(..., min_length=11, max_length=11, pattern=r'^\d+$')
    valor: float = Field(..., gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "cpf_destino": "12345678900",
                "valor": "100.00",
                
            }
        }

class SacarRequest(BaseModel):
    senha: str = Field(..., description="Senha da conta")
    valor: float = Field(..., gt=0, description="Valor a sacar (deve ser positivo)")

    class Config:
        json_schema_extra = {
            "example": {
                "senha": "senha123",
                "valor": "100.00",
                
            }
        }

class TransferenciaRequest(BaseModel):
    senha: str = Field(..., min_length=6, description="Senha da conta de origem")
    cpf_destino: str = Field(..., min_length=11, max_length=11, pattern=r'^\d+$', 
                            description="CPF da conta destino (apenas números)")
    valor: float = Field(..., gt=0, description="Valor a transferir (deve ser positivo)")

    @field_validator('cpf_destino')
    def validar_cpf_destino(cls, v):
        if len(v) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        return v

    @field_validator('valor')
    def validar_valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("Valor da transferência deve ser positivo")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "senha": "senha123",
                "cpf_destino": "12345678900",
                "valor": 150.50
            }
        }

class UsuarioResponse(BaseModel):
    nome: str
    cpf: str
    conta_id: int

class OperacaoRequest(BaseModel):
    senha: str  
    valor: float = Field(..., gt=0) 

class TransacaoResponse(BaseModel):
    valor: float
    tipo: str
    data: str
