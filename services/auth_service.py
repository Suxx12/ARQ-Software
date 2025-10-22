#!/usr/bin/env python3
"""
Servicio de Autenticación (AUTH) - Sistema de Reservación UDP
Puerto: 5001
Protocolo SOA: NNNNNSSSSSDATOS
"""
import socket
import threading
import json
import hashlib
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Cargar variables de entorno
load_dotenv('config.env')

class AuthService:
    """Servicio de Autenticación según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5001):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        
        # Configuración de base de datos
        DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./reservas_udp.db')
        self.engine = create_engine(DATABASE_URL)
        
        # Configuración JWT
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'tu_clave_secreta_muy_segura_aqui')
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    def create_access_token(self, data: dict):
        """Crear token JWT"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str):
        """Verificar token JWT"""
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def parse_message(self, message: str) -> tuple:
        """Parsear mensaje según protocolo SOA"""
        if len(message) < 10:
            raise ValueError("Mensaje muy corto")
        
        length_str = message[:5]
        service_code = message[5:10].strip()
        data_str = message[10:]
        
        try:
            data = json.loads(data_str) if data_str else {}
            return service_code, data
        except json.JSONDecodeError:
            raise ValueError("Error al decodificar JSON")
    
    def format_response(self, service_code: str, data: any) -> str:
        """Formatear respuesta según protocolo SOA"""
        json_data = json.dumps(data, ensure_ascii=False)
        service_code = service_code.ljust(5)[:5]
        message = service_code + json_data
        length_str = str(len(message)).zfill(5)
        
        return length_str + message
    
    def handle_login(self, data: dict) -> dict:
        """Manejar inicio de sesión"""
        try:
            # Parsear parámetros del mensaje
            rut = data.get('rut', '')
            password = data.get('pass', '')
            
            if not rut:
                return {"error": "RUT requerido"}
            
            with self.engine.connect() as conn:
                # Buscar usuario por RUT
                result = conn.execute(text(
                    "SELECT id_usuario, rut, correo_institucional, nombre, tipo_usuario FROM usuarios WHERE rut = :rut AND activo = 1"
                ), {"rut": rut})
                user = result.fetchone()
                
                if not user:
                    return {"error": "Credenciales inválidas"}
                
                # Crear token de acceso
                token_data = {
                    "sub": str(user[0]),
                    "rut": user[1],
                    "email": user[2],
                    "nombre": user[3],
                    "tipo_usuario": user[4]
                }
                
                access_token = self.create_access_token(token_data)
                
                return {
                    "token": access_token,
                    "ok": True,
                    "usuario": {
                        "id": user[0],
                        "rut": user[1],
                        "email": user[2],
                        "nombre": user[3],
                        "tipo_usuario": user[4]
                    }
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_refresh(self, data: dict) -> dict:
        """Manejar renovación de token"""
        try:
            token = data.get('refresh', '')
            
            if not token:
                return {"error": "Token requerido"}
            
            payload = self.verify_token(token)
            if payload is None:
                return {"error": "Token inválido"}
            
            # Crear nuevo token
            new_token = self.create_access_token(payload)
            
            return {
                "token": new_token,
                "ok": True
            }
            
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_logout(self, data: dict) -> dict:
        """Manejar cierre de sesión"""
        try:
            token = data.get('logout', '')
            
            if not token:
                return {"error": "Token requerido"}
            
            # Verificar token
            payload = self.verify_token(token)
            if payload is None:
                return {"error": "Token inválido"}
            
            return {"logout": True}
            
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "auth":
                return self.format_response("auth", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'rut' in data and 'pass' in data:
                response = self.handle_login(data)
            elif 'refresh' in data:
                response = self.handle_refresh(data)
            elif 'logout' in data:
                response = self.handle_logout(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("auth", response)
            
        except Exception as e:
            return self.format_response("auth", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[AUTH] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[AUTH] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[AUTH] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[AUTH] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[AUTH] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de autenticación"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[AUTH] Servicio de Autenticación iniciado en {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"[AUTH] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[AUTH] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de autenticación"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[AUTH] Servicio de Autenticación detenido")

def main():
    """Función principal"""
    service = AuthService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[AUTH] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()