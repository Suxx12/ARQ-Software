#!/usr/bin/env python3
"""
Servicio de Reservas (BOOK) - Sistema de Reservación UDP
Puerto: 5005
Protocolo SOA: NNNNNSSSSSDATOS
"""
import socket
import threading
import json
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# Cargar variables de entorno
load_dotenv('config.env')

class BookingService:
    """Servicio de Reservas según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5005):
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
    
    def handle_create_booking(self, data: dict) -> dict:
        """Crear nueva reserva"""
        try:
            user_id = data.get('user', '')
            space_id = data.get('space', '')
            inicio = data.get('inicio', '')
            fin = data.get('fin', '')
            motivo = data.get('motivo', '')
            
            if not all([user_id, space_id, inicio, fin]):
                return {"error": "Usuario, espacio, inicio y fin son requeridos"}
            
            # Parsear fechas
            try:
                fecha_inicio = datetime.fromisoformat(inicio.replace('T', ' '))
                fecha_fin = datetime.fromisoformat(fin.replace('T', ' '))
                
                if fecha_fin <= fecha_inicio:
                    return {"error": "La fecha de fin debe ser posterior a la de inicio"}
                
            except ValueError as e:
                return {"error": f"Formato de fecha inválido: {str(e)}"}
            
            with self.engine.connect() as conn:
                # Verificar que el usuario existe
                user_result = conn.execute(text(
                    "SELECT id_usuario FROM usuarios WHERE id_usuario = :user_id AND activo = 1"
                ), {"user_id": user_id})
                
                if not user_result.fetchone():
                    return {"error": "Usuario no encontrado"}
                
                # Verificar que el espacio existe
                space_result = conn.execute(text(
                    "SELECT id_espacio FROM espacios WHERE id_espacio = :space_id AND activo = 1"
                ), {"space_id": space_id})
                
                if not space_result.fetchone():
                    return {"error": "Espacio no encontrado"}
                
                # Verificar disponibilidad
                conflict_result = conn.execute(text("""
                    SELECT COUNT(*) FROM reservas 
                    WHERE id_espacio = :space_id 
                    AND estado IN ('pendiente', 'aprobada')
                    AND (
                        (fecha_inicio < :fecha_fin AND fecha_fin > :fecha_inicio)
                    )
                """), {
                    "space_id": space_id,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin
                })
                
                if conflict_result.fetchone()[0] > 0:
                    return {"error": "El espacio no está disponible en ese horario"}
                
                # Crear reserva
                result = conn.execute(text("""
                    INSERT INTO reservas (id_usuario, id_espacio, fecha_inicio, fecha_fin, 
                                        estado, motivo, fecha_solicitud, tipo_reserva)
                    VALUES (:user_id, :space_id, :fecha_inicio, :fecha_fin, 
                            'pendiente', :motivo, :fecha_solicitud, 'normal')
                """), {
                    "user_id": user_id,
                    "space_id": space_id,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "motivo": motivo,
                    "fecha_solicitud": datetime.now()
                })
                
                conn.commit()
                
                # Obtener ID de la reserva creada
                booking_result = conn.execute(text("""
                    SELECT id_reserva FROM reservas 
                    WHERE id_usuario = :user_id AND id_espacio = :space_id 
                    AND fecha_inicio = :fecha_inicio AND fecha_fin = :fecha_fin
                    ORDER BY fecha_solicitud DESC LIMIT 1
                """), {
                    "user_id": user_id,
                    "space_id": space_id,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin
                })
                
                booking_id = booking_result.fetchone()[0]
                
                return {
                    "id": booking_id,
                    "estado": "pendiente"
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_approve_booking(self, data: dict) -> dict:
        """Aprobar o rechazar reserva"""
        try:
            reserva_id = data.get('reserva', '')
            estado = data.get('estado', '')
            admin_id = data.get('admin', '')
            
            if not all([reserva_id, estado, admin_id]):
                return {"error": "ID de reserva, estado y admin son requeridos"}
            
            valid_states = ['aprobada', 'rechazada']
            if estado not in valid_states:
                return {"error": f"Estado inválido. Estados válidos: {valid_states}"}
            
            with self.engine.connect() as conn:
                # Verificar que la reserva existe
                reserva_result = conn.execute(text(
                    "SELECT id_reserva FROM reservas WHERE id_reserva = :reserva_id"
                ), {"reserva_id": reserva_id})
                
                if not reserva_result.fetchone():
                    return {"error": "Reserva no encontrada"}
                
                # Actualizar estado
                conn.execute(text("""
                    UPDATE reservas SET estado = :estado WHERE id_reserva = :reserva_id
                """), {"estado": estado, "reserva_id": reserva_id})
                
                conn.commit()
                
                return {
                    "updated": True,
                    "notificado": True  # Se podría implementar notificación real
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_user_bookings(self, data: dict) -> dict:
        """Obtener reservas de un usuario"""
        try:
            user_id = data.get('user', '')
            
            if not user_id:
                return {"error": "ID de usuario es requerido"}
            
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT r.id_reserva, e.nombre, r.fecha_inicio, r.fecha_fin, 
                           r.estado, r.motivo, r.fecha_solicitud
                    FROM reservas r
                    JOIN espacios e ON r.id_espacio = e.id_espacio
                    WHERE r.id_usuario = :user_id
                    ORDER BY r.fecha_solicitud DESC
                """), {"user_id": user_id})
                
                bookings = []
                for row in result:
                    bookings.append({
                        "id": row[0],
                        "espacio": row[1],
                        "fecha_inicio": row[2].isoformat(),
                        "fecha_fin": row[3].isoformat(),
                        "estado": row[4],
                        "motivo": row[5],
                        "fecha_solicitud": row[6].isoformat()
                    })
                
                return bookings
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_cancel_booking(self, data: dict) -> dict:
        """Cancelar reserva"""
        try:
            reserva_id = data.get('reserva', '')
            user_id = data.get('user', '')
            
            if not reserva_id:
                return {"error": "ID de reserva es requerido"}
            
            with self.engine.connect() as conn:
                # Verificar que la reserva existe y pertenece al usuario
                reserva_result = conn.execute(text("""
                    SELECT id_reserva FROM reservas 
                    WHERE id_reserva = :reserva_id AND id_usuario = :user_id
                """), {"reserva_id": reserva_id, "user_id": user_id})
                
                if not reserva_result.fetchone():
                    return {"error": "Reserva no encontrada o no autorizada"}
                
                # Cancelar reserva
                conn.execute(text("""
                    UPDATE reservas SET estado = 'cancelada' WHERE id_reserva = :reserva_id
                """), {"reserva_id": reserva_id})
                
                conn.commit()
                
                return {"cancelled": True}
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "book":
                return self.format_response("book", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'user' in data and 'space' in data and 'inicio' in data and 'fin' in data:
                response = self.handle_create_booking(data)
            elif 'approve' in data or ('reserva' in data and 'estado' in data and 'admin' in data):
                response = self.handle_approve_booking(data)
            elif 'getmyreservas' in data or ('user' in data and 'action' in data and data['action'] == 'get'):
                response = self.handle_get_user_bookings(data)
            elif 'cancel' in data or ('reserva' in data and 'action' in data and data['action'] == 'cancel'):
                response = self.handle_cancel_booking(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("book", response)
            
        except Exception as e:
            return self.format_response("book", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[BOOK] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[BOOK] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[BOOK] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[BOOK] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[BOOK] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de reservas"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[BOOK] Servicio de Reservas iniciado en {self.host}:{self.port}")
            
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
                        print(f"[BOOK] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[BOOK] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de reservas"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[BOOK] Servicio de Reservas detenido")

def main():
    """Función principal"""
    service = BookingService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[BOOK] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()