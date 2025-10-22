#!/usr/bin/env python3
"""
Servicio de Espacios (SPACE) - Sistema de Reservación UDP
Puerto: 5003
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

class SpaceService:
    """Servicio de Espacios según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5003):
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
    
    def handle_create_space(self, data: dict) -> dict:
        """Crear nuevo espacio"""
        try:
            nombre = data.get('nombre', '')
            tipo = data.get('tipo', 'sala')
            capacidad = data.get('capacidad', 10)
            
            if not nombre:
                return {"error": "Nombre del espacio es requerido"}
            
            valid_types = ['sala', 'cancha']
            if tipo not in valid_types:
                return {"error": f"Tipo inválido. Tipos válidos: {valid_types}"}
            
            with self.engine.connect() as conn:
                # Verificar si el espacio ya existe
                result = conn.execute(text(
                    "SELECT id_espacio FROM espacios WHERE nombre = :nombre"
                ), {"nombre": nombre})
                
                if result.fetchone():
                    return {"error": "Espacio ya existe"}
                
                # Crear espacio
                result = conn.execute(text("""
                    INSERT INTO espacios (nombre, tipo, capacidad, activo)
                    VALUES (:nombre, :tipo, :capacidad, 1)
                """), {
                    "nombre": nombre,
                    "tipo": tipo,
                    "capacidad": capacidad
                })
                
                conn.commit()
                
                # Obtener ID del espacio creado
                result = conn.execute(text(
                    "SELECT id_espacio FROM espacios WHERE nombre = :nombre"
                ), {"nombre": nombre})
                space_id = result.fetchone()[0]
                
                return {
                    "id": space_id,
                    "status": "created"
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_all_spaces(self, data: dict) -> dict:
        """Obtener todos los espacios"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id_espacio, nombre, tipo, capacidad, activo
                    FROM espacios ORDER BY nombre
                """))
                
                spaces = []
                for row in result:
                    spaces.append({
                        "id": row[0],
                        "nombre": row[1],
                        "tipo": row[2],
                        "capacidad": row[3],
                        "activo": bool(row[4])
                    })
                
                return spaces
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_update_space(self, data: dict) -> dict:
        """Actualizar espacio"""
        try:
            space_id = data.get('id', '')
            nombre = data.get('nombre', '')
            tipo = data.get('tipo', '')
            capacidad = data.get('capacidad', '')
            
            if not space_id:
                return {"error": "ID del espacio es requerido"}
            
            with self.engine.connect() as conn:
                # Verificar que el espacio existe
                result = conn.execute(text(
                    "SELECT id_espacio FROM espacios WHERE id_espacio = :space_id"
                ), {"space_id": space_id})
                
                if not result.fetchone():
                    return {"error": "Espacio no encontrado"}
                
                # Construir query de actualización
                updates = []
                params = {"space_id": space_id}
                
                if nombre:
                    updates.append("nombre = :nombre")
                    params["nombre"] = nombre
                
                if tipo:
                    valid_types = ['sala', 'cancha']
                    if tipo not in valid_types:
                        return {"error": f"Tipo inválido. Tipos válidos: {valid_types}"}
                    updates.append("tipo = :tipo")
                    params["tipo"] = tipo
                
                if capacidad:
                    updates.append("capacidad = :capacidad")
                    params["capacidad"] = capacidad
                
                if not updates:
                    return {"error": "No hay campos para actualizar"}
                
                # Ejecutar actualización
                query = f"UPDATE espacios SET {', '.join(updates)} WHERE id_espacio = :space_id"
                conn.execute(text(query), params)
                conn.commit()
                
                return {"updated": True}
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_delete_space(self, data: dict) -> dict:
        """Eliminar espacio (desactivar)"""
        try:
            space_id = data.get('id', '')
            
            if not space_id:
                return {"error": "ID del espacio es requerido"}
            
            with self.engine.connect() as conn:
                # Verificar que el espacio existe
                result = conn.execute(text(
                    "SELECT id_espacio FROM espacios WHERE id_espacio = :space_id"
                ), {"space_id": space_id})
                
                if not result.fetchone():
                    return {"error": "Espacio no encontrado"}
                
                # Desactivar espacio
                conn.execute(text("""
                    UPDATE espacios SET activo = 0 WHERE id_espacio = :space_id
                """), {"space_id": space_id})
                
                conn.commit()
                
                return {"deleted": True}
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "space":
                return self.format_response("space", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'create' in data or ('nombre' in data and 'tipo' in data):
                response = self.handle_create_space(data)
            elif 'getall' in data or data == {}:
                response = self.handle_get_all_spaces(data)
            elif 'update' in data or ('id' in data and ('nombre' in data or 'tipo' in data or 'capacidad' in data)):
                response = self.handle_update_space(data)
            elif 'delete' in data or ('id' in data and 'action' in data and data['action'] == 'delete'):
                response = self.handle_delete_space(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("space", response)
            
        except Exception as e:
            return self.format_response("space", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[SPACE] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[SPACE] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[SPACE] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[SPACE] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[SPACE] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de espacios"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[SPACE] Servicio de Espacios iniciado en {self.host}:{self.port}")
            
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
                        print(f"[SPACE] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[SPACE] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de espacios"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[SPACE] Servicio de Espacios detenido")

def main():
    """Función principal"""
    service = SpaceService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[SPACE] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()