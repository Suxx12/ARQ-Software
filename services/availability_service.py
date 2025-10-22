#!/usr/bin/env python3
"""
Servicio de Disponibilidad (AVAIL) - Sistema de Reservación UDP
Puerto: 5004
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

class AvailabilityService:
    """Servicio de Disponibilidad según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5004):
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
    
    def handle_check_availability(self, data: dict) -> dict:
        """Consultar disponibilidad de espacios"""
        try:
            fecha = data.get('fecha', '')
            hora = data.get('hora', '')
            duracion = data.get('duracion', 1)
            tipo_espacio = data.get('tipo', '')
            
            if not fecha:
                return {"error": "Fecha es requerida"}
            
            # Parsear fecha y hora
            try:
                if hora:
                    start_datetime = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
                else:
                    start_datetime = datetime.strptime(fecha, "%Y-%m-%d")
                    start_datetime = start_datetime.replace(hour=8)  # Hora por defecto
                
                end_datetime = start_datetime + timedelta(hours=int(duracion))
                
            except ValueError as e:
                return {"error": f"Formato de fecha/hora inválido: {str(e)}"}
            
            with self.engine.connect() as conn:
                # Obtener todos los espacios activos
                spaces_query = "SELECT id_espacio, nombre, tipo, capacidad FROM espacios WHERE activo = 1"
                params = {}
                
                if tipo_espacio:
                    spaces_query += " AND tipo = :tipo"
                    params["tipo"] = tipo_espacio
                
                spaces_result = conn.execute(text(spaces_query), params)
                spaces = []
                
                for space_row in spaces_result:
                    space_id = space_row[0]
                    
                    # Verificar si hay reservas conflictivas
                    conflict_query = text("""
                        SELECT COUNT(*) FROM reservas 
                        WHERE id_espacio = :space_id 
                        AND estado IN ('pendiente', 'aprobada')
                        AND (
                            (fecha_inicio < :end_time AND fecha_fin > :start_time)
                        )
                    """)
                    
                    conflict_result = conn.execute(conflict_query, {
                        "space_id": space_id,
                        "start_time": start_datetime,
                        "end_time": end_datetime
                    })
                    
                    conflict_count = conflict_result.fetchone()[0]
                    disponible = conflict_count == 0
                    
                    spaces.append({
                        "id": space_id,
                        "nombre": space_row[1],
                        "tipo": space_row[2],
                        "capacidad": space_row[3],
                        "disponible": disponible,
                        "horarios": []
                    })
                
                return spaces
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_calendar(self, data: dict) -> dict:
        """Consultar calendario de un espacio específico"""
        try:
            space_id = data.get('space', '')
            fecha = data.get('fecha', '')
            
            if not all([space_id, fecha]):
                return {"error": "ID del espacio y fecha son requeridos"}
            
            # Parsear fecha
            try:
                target_date = datetime.strptime(fecha, "%Y-%m-%d")
                start_of_day = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
                end_of_day = target_date.replace(hour=22, minute=0, second=0, microsecond=0)
                
            except ValueError as e:
                return {"error": f"Formato de fecha inválido: {str(e)}"}
            
            with self.engine.connect() as conn:
                # Verificar que el espacio existe
                space_result = conn.execute(text(
                    "SELECT nombre FROM espacios WHERE id_espacio = :space_id AND activo = 1"
                ), {"space_id": space_id})
                
                space_name = space_result.fetchone()
                if not space_name:
                    return {"error": "Espacio no encontrado"}
                
                # Obtener reservas del día
                reservations_result = conn.execute(text("""
                    SELECT fecha_inicio, fecha_fin, estado, motivo
                    FROM reservas 
                    WHERE id_espacio = :space_id 
                    AND fecha_inicio >= :start_of_day 
                    AND fecha_fin <= :end_of_day
                    ORDER BY fecha_inicio
                """), {
                    "space_id": space_id,
                    "start_of_day": start_of_day,
                    "end_of_day": end_of_day
                })
                
                # Generar horarios por hora
                horarios = []
                current_time = start_of_day
                
                while current_time < end_of_day:
                    next_hour = current_time + timedelta(hours=1)
                    
                    # Verificar si hay reserva en este horario
                    reserva_info = None
                    for res_row in reservations_result.fetchall():
                        res_start, res_end, estado, motivo = res_row
                        if res_start <= current_time < res_end:
                            reserva_info = {
                                "reserva_id": None,  # Se podría agregar ID si es necesario
                                "estado": estado,
                                "motivo": motivo
                            }
                            break
                    
                    horarios.append({
                        "hora": current_time.strftime("%H:%M"),
                        "disponible": reserva_info is None,
                        "reserva_id": reserva_info["reserva_id"] if reserva_info else None,
                        "estado": reserva_info["estado"] if reserva_info else None,
                        "motivo": reserva_info["motivo"] if reserva_info else None
                    })
                    
                    current_time = next_hour
                
                return {
                    "espacio": space_name[0],
                    "fecha": fecha,
                    "horarios": horarios
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "avail":
                return self.format_response("avail", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'fecha' in data and 'hora' in data:
                response = self.handle_check_availability(data)
            elif 'calendar' in data or ('space' in data and 'fecha' in data):
                response = self.handle_get_calendar(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("avail", response)
            
        except Exception as e:
            return self.format_response("avail", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[AVAIL] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[AVAIL] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[AVAIL] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[AVAIL] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[AVAIL] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de disponibilidad"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[AVAIL] Servicio de Disponibilidad iniciado en {self.host}:{self.port}")
            
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
                        print(f"[AVAIL] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[AVAIL] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de disponibilidad"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[AVAIL] Servicio de Disponibilidad detenido")

def main():
    """Función principal"""
    service = AvailabilityService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[AVAIL] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()