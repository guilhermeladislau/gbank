from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer
from . import models, schemas
from .database import get_db, engine
from .auth import (pwd_context, criar_token_jwt, verificar_senha, obter_usuario_logado,obter_conta, autenticar_usuario, autenticar_por_senha)
from sqlalchemy.orm import Session
from datetime import datetime
from .schemas import TransferenciaRequest, OperacaoRequest, SacarRequest
from .models import Base

app = FastAPI()
Base.metadata.create_all(bind=engine)

@app.get("/usuario/atual")
def usuario_atual(
    request: Request,
    db: Session = Depends(get_db)
):
    
    """
    Veja em qual conta está logado
    """

    usuario = obter_usuario_logado(request, db)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado"
        )
    
    cpf_formatado = f"{usuario.cpf[:3]}.{usuario.cpf[3:6]}.{usuario.cpf[6:9]}-{usuario.cpf[9:]}"
     
    return {
        "mensagem": f"A conta logada está no nome de: {usuario.nome}, CPF: {cpf_formatado}",
        }

@app.post("/cadastrar", status_code=status.HTTP_201_CREATED)
def cadastrar(
    usuario: schemas.UsuarioCreate,
    response: Response,
    db: Session = Depends(get_db)
):
    
    """
    Cadastre uma nova conta
    """

    if db.query(models.Usuario).filter(models.Usuario.cpf == usuario.cpf).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF já cadastrado"
        )
    
    senha_hash = pwd_context.hash(usuario.senha)
    novo_usuario = models.Usuario(
        nome=usuario.nome,
        cpf=usuario.cpf,
        senha_hash=senha_hash
    )
    db.add(novo_usuario)
    db.flush()
    
    nova_conta = models.Conta(usuario_id=novo_usuario.id, saldo=0.0)
    db.add(nova_conta)
    db.commit()
    
    return {"mensagem": "Usuário cadastrado com sucesso"}

@app.post("/login")
def login(
    response: Response,
    login_data: schemas.LoginRequest, 
    db: Session = Depends(get_db)
):
    
    """
    Entre em uma conta existente
    """

    usuario = db.query(models.Usuario).filter(models.Usuario.cpf == login_data.cpf).first()
    
    if not usuario or not verificar_senha(login_data.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF ou senha incorretos"
        )
    
    token = criar_token_jwt(usuario.cpf)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=1800,
        secure=False,
        samesite="lax"
    )
    
    return {
        "mensagem": "Login bem-sucedido",
        "nome_usuario": usuario.nome,
        "conta_id": usuario.contas[0].id
    }



def requer_autenticacao(request: Request, db: Session = Depends(get_db)):
    usuario = obter_usuario_logado(request, db)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso não autorizado"
        )
    return usuario



@app.post("/depositar")
def depositar(
    dados: schemas.DepositoRequest,
    usuario: models.Usuario = Depends(requer_autenticacao),
    db: Session = Depends(get_db)
):
    
    """
    Deposite dinheiro
    """

    conta = db.query(models.Conta).filter(models.Conta.usuario_id == usuario.id).first()
    if not conta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada"
        )
    
    if dados.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor deve ser positivo"
        )
    
    conta.saldo += dados.valor
    transacao = models.Transacao(
        valor=dados.valor,
        tipo="depósito",
        conta_id=conta.id
    )
    db.add(transacao)
    db.commit()
    
    return {
        "mensagem": "Depósito realizado",
        "saldo_atual": conta.saldo
    }

@app.post("/sacar")
def sacar(
    request: Request,
    operacao: SacarRequest,
    db: Session = Depends(get_db)
):
    
    """
    Realize um saque
    """

    usuario = obter_usuario_logado(request, db)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faça login primeiro"
        )
    
    usuario = autenticar_por_senha(db, usuario.cpf, operacao.senha)
    conta = obter_conta(db, usuario)

    # Validações
    if operacao.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor do saque deve ser positivo"
        )
    
    if conta.saldo < operacao.valor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Saldo insuficiente"
        )

    conta.saldo -= operacao.valor

    nova_transacao = models.Transacao(
        valor=operacao.valor,
        tipo="saque",
        conta_id=conta.id
    )
    db.add(nova_transacao)
    db.commit()

    return {
        "mensagem": "Saque realizado com sucesso",
        "saldo_atual": conta.saldo}


@app.post("/transferir")
def transferir(
    cpf_origem: str,
    operacao: TransferenciaRequest,
    db: Session = Depends(get_db)
):
    
    """
    Transfira dinheiro entre contas
    """

    usuario_origem = autenticar_usuario(db, cpf_origem, operacao.senha)
    conta_origem = obter_conta(db, usuario_origem)

    if operacao.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor da transferência deve ser positivo"
        )
    
    if conta_origem.saldo < operacao.valor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Saldo insuficiente"
        )

    conta_destino = db.query(models.Conta).join(models.Usuario).filter(
        models.Usuario.cpf == operacao.cpf_destino
    ).first()
    
    if not conta_destino:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta destino não encontrada"
        )

    conta_origem.saldo -= operacao.valor
    conta_destino.saldo += operacao.valor

    transacao_origem = models.Transacao(
        valor=operacao.valor,
        tipo="transferência_enviada",
        conta_id=conta_origem.id
    )
    transacao_destino = models.Transacao(
        valor=operacao.valor,
        tipo="transferência_recebida",
        conta_id=conta_destino.id
    )
    
    db.add_all([transacao_origem, transacao_destino])
    db.commit()

    return {
        "mensagem": "Transferência realizada com sucesso",
        "saldo_atual": conta_origem.saldo
    }

@app.get("/extrato")
def ver_extrato(
    usuario: models.Usuario = Depends(requer_autenticacao),
    db: Session = Depends(get_db)
):
    
    """
    Verifique o extrato da conta
    """
    
    conta = db.query(models.Conta).filter(models.Conta.usuario_id == usuario.id).first()
    if not conta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada"
        )
    
    transacoes = db.query(models.Transacao).filter(
        models.Transacao.conta_id == conta.id
    ).all()
    
    return {
        "saldo_atual": conta.saldo,
        "transacoes": transacoes
    }

@app.post("/logout")
def logout(response: Response):
    """
    Saia da conta logada
    """    
    response.delete_cookie("access_token")
    return {"mensagem": "Logout realizado"}





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)