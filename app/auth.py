from fastapi import HTTPException, status, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import os
from . import models
from sqlalchemy.orm import Session


SECRET_KEY = "chave-secreta-para-assinatura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_senha(senha: str, senha_hash: str):
    return pwd_context.verify(senha, senha_hash)

def criar_token_jwt(cpf: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": cpf, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def autenticar_usuario(db: Session, cpf: str, senha: str) -> models.Usuario:
    usuario = db.query(models.Usuario).filter(models.Usuario.cpf == cpf).first()
    
    if not usuario or not verificar_senha(senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF ou senha incorretos"
        )
    return usuario

def autenticar_por_senha(db: Session, cpf: str, senha: str) -> models.Usuario:
    usuario = db.query(models.Usuario).filter(models.Usuario.cpf == cpf).first()
    
    if not usuario or not pwd_context.verify(senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha incorreta"
        )
    return usuario

def obter_conta(db: Session, usuario: models.Usuario) -> models.Conta:
    conta = db.query(models.Conta).filter(models.Conta.usuario_id == usuario.id).first()
    if not conta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada"
        )
    return conta

def obter_usuario_logado(request: Request, db: Session) -> models.Usuario | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cpf = payload.get("sub")
        if not cpf:
            return None
        
        return db.query(models.Usuario).filter(models.Usuario.cpf == cpf).first()
    except JWTError:
        return None