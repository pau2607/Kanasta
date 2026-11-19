"""Acceso de administrador.

Usuario y contraseña por defecto:  admin / kanasta2026
La contraseña no se guarda en texto plano: se guarda su hash PBKDF2-SHA256 con sal.
Para cambiarla, genera un hash nuevo con `generar_hash("nueva_clave")` y reemplaza las constantes.
"""
from __future__ import annotations

import hashlib
import hmac
import os

import streamlit as st

ADMIN_USUARIO = os.getenv("MKT_ADMIN_USER", "admin")
_SAL = "7f1a6012c813d099a52f0271a3b3be20"
_HASH = "e131adac3b005a42543bc649a7c44157fb4f668dd41bb0e1c41001a48215bbba"
_ITER = 200_000


def generar_hash(clave: str, sal_hex: str = _SAL) -> str:
    return hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal_hex), _ITER).hex()


def verificar(usuario: str, clave: str) -> bool:
    ok_usuario = hmac.compare_digest(usuario.strip().lower(), ADMIN_USUARIO)
    ok_clave = hmac.compare_digest(generar_hash(clave), _HASH)
    return ok_usuario and ok_clave


def es_admin() -> bool:
    return st.session_state.get("rol") == "admin"


def iniciar_sesion_admin():
    st.session_state["rol"] = "admin"


def cerrar_sesion_admin():
    st.session_state["rol"] = "cliente"
