from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(11), unique=True, nullable=False)
    senha_hash = Column(String(200), nullable=False)
    contas = relationship("Conta", back_populates="usuario")

class Conta(Base):
    __tablename__ = "contas"

    id = Column(Integer, primary_key=True, index=True)
    saldo = Column(Float, default=0.0)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    usuario = relationship("Usuario", back_populates="contas")
    transacoes = relationship("Transacao", back_populates="conta")

class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Float, nullable=False)
    tipo = Column(String(20), nullable=False)
    data = Column(DateTime, default=datetime.utcnow)
    conta_id = Column(Integer, ForeignKey("contas.id"))
    conta = relationship("Conta", back_populates="transacoes")