#!/usr/bin/env python3
"""
Servicio de Usuarios (USER) - Sistema de Reservación UDP
Puerto: 5002
Protocolo SOA: NNNNNSSSSSDATOS
"""
import socket
import threading
import json
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime

# Cargar variables de entorno
load_dotenv('config.env')

class UserService:
    """Servicio de Usuarios según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5002):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        
        # Configuración de base de datos
        DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./reservas_udp.db')
        self.engine = create_engine(DATABASE_URL)
    
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
    
    def handle_create_user(self, data: dict) -> dict:
        """Crear nuevo usuario"""
        try:
            rut = data.get('rut', '')
            correo = data.get('correo', '')
            nombre = data.get('nombre', '')
            tipo = data.get('tipo', 'estudiante')
            
            if not all([rut, correo, nombre]):
                return {"error": "RUT, correo y nombre son requeridos"}
            
            with self.engine.connect() as conn:
                # Verificar si el usuario ya existe
                result = conn.execute(text(
                    "SELECT id_usuario FROM usuarios WHERE rut = :rut OR correo_institucional = :correo"
                ), {"rut": rut, "correo": correo})
                
                if result.fetchone():
                    return {"error": "Usuario ya existe"}
                
                # Crear usuario
                result = conn.execute(text("""
                    INSERT INTO usuarios (rut, correo_institucional, nombre, tipo_usuario, activo, fecha_creacion)
                    VALUES (:rut, :correo, :nombre, :tipo, 1, :fecha)
                """), {
                    "rut": rut,
                    "correo": correo,
                    "nombre": nombre,
                    "tipo": tipo,
                    "fecha": datetime.now()
                })
                
                conn.commit()
                
                # Obtener ID del usuario creado
                result = conn.execute(text(
                    "SELECT id_usuario FROM usuarios WHERE rut = :rut"
                ), {"rut": rut})
                user_id = result.fetchone()[0]
                
                return {
                    "id": user_id,
                    "status": "created"
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_all_users(self, data: dict) -> dict:
        """Obtener todos los usuarios"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id_usuario, rut, correo_institucional, nombre, tipo_usuario, activo
                    FROM usuarios ORDER BY fecha_creacion DESC
                """))
                
                users = []
                for row in result:
                    users.append({
                        "id": row[0],
                        "rut": row[1],
                        "correo": row[2],
                        "nombre": row[3],
                        "tipo": row[4],
                        "activo": bool(row[5])
                    })
                
                return users
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_change_role(self, data: dict) -> dict:
        """Cambiar rol de usuario"""
        try:
            user_id = data.get('user', '')
            new_role = data.get('rol', '')
            
            if not all([user_id, new_role]):
                return {"error": "ID de usuario y nuevo rol son requeridos"}
            
            valid_roles = ['estudiante', 'funcionario', 'administrador']
            if new_role not in valid_roles:
                return {"error": f"Rol inválido. Roles válidos: {valid_roles}"}
            
            with self.engine.connect() as conn:
                # Verificar que el usuario existe
                result = conn.execute(text(
                    "SELECT id_usuario FROM usuarios WHERE id_usuario = :user_id"
                ), {"user_id": user_id})
                
                if not result.fetchone():
                    return {"error": "Usuario no encontrado"}
                
                # Actualizar rol
                conn.execute(text("""
                    UPDATE usuarios SET tipo_usuario = :new_role WHERE id_usuario = :user_id
                """), {"new_role": new_role, "user_id": user_id})
                
                conn.commit()
                
                return {"updated": True}
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_deactivate_user(self, data: dict) -> dict:
        """Desactivar usuario"""
        try:
            user_id = data.get('user', '')
            
            if not user_id:
                return {"error": "ID de usuario es requerido"}
            
            with self.engine.connect() as conn:
                # Verificar que el usuario existe
                result = conn.execute(text(
                    "SELECT id_usuario FROM usuarios WHERE id_usuario = :user_id"
                ), {"user_id": user_id})
                
                if not result.fetchone():
                    return {"error": "Usuario no encontrado"}
                
                # Desactivar usuario
                conn.execute(text("""
                    UPDATE usuarios SET activo = 0 WHERE id_usuario = :user_id
                """), {"user_id": user_id})
                
                conn.commit()
                
                return {"deactivated": True}
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "user":
                return self.format_response("user", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'create' in data or ('rut' in data and 'correo' in data and 'nombre' in data):
                response = self.handle_create_user(data)
            elif 'getall' in data or data == {}:
                response = self.handle_get_all_users(data)
            elif 'changerole' in data or ('user' in data and 'rol' in data):
                response = self.handle_change_role(data)
            elif 'deactivate' in data or ('user' in data and 'action' in data and data['action'] == 'deactivate'):
                response = self.handle_deactivate_user(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("user", response)
            
        except Exception as e:
            return self.format_response("user", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[USER] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[USER] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[USER] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[USER] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[USER] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de usuarios"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[USER] Servicio de Usuarios iniciado en {self.host}:{self.port}")
            
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
                        print(f"[USER] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[USER] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de usuarios"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[USER] Servicio de Usuarios detenido")

def main():
    """Función principal"""
    service = UserService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[USER] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()