#!/usr/bin/env python3
"""
Servicio de Incidencias (INCID) - Sistema de Reservación UDP
Puerto: 5006
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

class IncidentService:
    """Servicio de Incidencias según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5006):
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
    
    def handle_report_incident(self, data: dict) -> dict:
        """Reportar nueva incidencia"""
        try:
            space_id = data.get('space', '')
            tipo = data.get('tipo', '')
            descripcion = data.get('descripcion', '')
            user_id = data.get('user', '')
            
            if not all([space_id, tipo, descripcion]):
                return {"error": "Espacio, tipo y descripción son requeridos"}
            
            valid_types = ['mantencion', 'averia', 'limpieza', 'otro']
            if tipo not in valid_types:
                return {"error": f"Tipo inválido. Tipos válidos: {valid_types}"}
            
            with self.engine.connect() as conn:
                # Verificar que el espacio existe
                space_result = conn.execute(text(
                    "SELECT id_espacio FROM espacios WHERE id_espacio = :space_id AND activo = 1"
                ), {"space_id": space_id})
                
                if not space_result.fetchone():
                    return {"error": "Espacio no encontrado"}
                
                # Crear incidencia
                result = conn.execute(text("""
                    INSERT INTO incidencias (id_espacio, tipo, descripcion, estado, 
                                           fecha_reporte, id_usuario_reporte)
                    VALUES (:space_id, :tipo, :descripcion, 'abierta', 
                            :fecha_reporte, :user_id)
                """), {
                    "space_id": space_id,
                    "tipo": tipo,
                    "descripcion": descripcion,
                    "fecha_reporte": datetime.now(),
                    "user_id": user_id
                })
                
                conn.commit()
                
                # Obtener ID de la incidencia creada
                incident_result = conn.execute(text("""
                    SELECT id_incidencia FROM incidencias 
                    WHERE id_espacio = :space_id AND descripcion = :descripcion
                    ORDER BY fecha_reporte DESC LIMIT 1
                """), {"space_id": space_id, "descripcion": descripcion})
                
                incident_id = incident_result.fetchone()[0]
                
                return {
                    "id_incidencia": incident_id,
                    "estado": "abierta"
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_apply_block(self, data: dict) -> dict:
        """Aplicar bloqueo por incidencia"""
        try:
            incidencia_id = data.get('incidencia', '')
            inicio = data.get('inicio', '')
            fin = data.get('fin', '')
            
            if not all([incidencia_id, inicio, fin]):
                return {"error": "ID de incidencia, inicio y fin son requeridos"}
            
            # Parsear fechas
            try:
                fecha_inicio = datetime.fromisoformat(inicio.replace('T', ' '))
                fecha_fin = datetime.fromisoformat(fin.replace('T', ' '))
                
                if fecha_fin <= fecha_inicio:
                    return {"error": "La fecha de fin debe ser posterior a la de inicio"}
                
            except ValueError as e:
                return {"error": f"Formato de fecha inválido: {str(e)}"}
            
            with self.engine.connect() as conn:
                # Verificar que la incidencia existe
                incident_result = conn.execute(text("""
                    SELECT id_espacio FROM incidencias WHERE id_incidencia = :incidencia_id
                """), {"incidencia_id": incidencia_id})
                
                incident_row = incident_result.fetchone()
                if not incident_row:
                    return {"error": "Incidencia no encontrada"}
                
                space_id = incident_row[0]
                
                # Cancelar reservas afectadas
                cancel_result = conn.execute(text("""
                    UPDATE reservas SET estado = 'cancelada' 
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
                
                reservas_canceladas = cancel_result.rowcount
                
                # Crear bloqueo
                conn.execute(text("""
                    INSERT INTO reservas (id_espacio, fecha_inicio, fecha_fin, estado, 
                                        motivo, fecha_solicitud, tipo_reserva, descripcion_incidencia)
                    VALUES (:space_id, :fecha_inicio, :fecha_fin, 'bloqueo', 
                            'Bloqueo por incidencia', :fecha_solicitud, 'bloqueo', :descripcion)
                """), {
                    "space_id": space_id,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "fecha_solicitud": datetime.now(),
                    "descripcion": f"Incidencia #{incidencia_id}"
                })
                
                conn.commit()
                
                return {
                    "bloqueado": True,
                    "reservas_canceladas": reservas_canceladas
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_resolve_incident(self, data: dict) -> dict:
        """Resolver incidencia"""
        try:
            incidencia_id = data.get('incidencia', '')
            solucion = data.get('solucion', '')
            
            if not incidencia_id:
                return {"error": "ID de incidencia es requerido"}
            
            with self.engine.connect() as conn:
                # Verificar que la incidencia existe
                incident_result = conn.execute(text("""
                    SELECT id_espacio FROM incidencias WHERE id_incidencia = :incidencia_id
                """), {"incidencia_id": incidencia_id})
                
                incident_row = incident_result.fetchone()
                if not incident_row:
                    return {"error": "Incidencia no encontrada"}
                
                space_id = incident_row[0]
                
                # Marcar incidencia como resuelta
                conn.execute(text("""
                    UPDATE incidencias SET estado = 'resuelta', solucion = :solucion, 
                                         fecha_resolucion = :fecha_resolucion
                    WHERE id_incidencia = :incidencia_id
                """), {
                    "solucion": solucion,
                    "fecha_resolucion": datetime.now(),
                    "incidencia_id": incidencia_id
                })
                
                # Eliminar bloqueos activos del espacio
                block_result = conn.execute(text("""
                    DELETE FROM reservas 
                    WHERE id_espacio = :space_id AND tipo_reserva = 'bloqueo' AND estado = 'bloqueo'
                """), {"space_id": space_id})
                
                conn.commit()
                
                return {
                    "resuelta": True,
                    "espacio_liberado": True
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_incidents(self, data: dict) -> dict:
        """Obtener incidencias"""
        try:
            estado = data.get('estado', '')
            space_id = data.get('space', '')
            
            with self.engine.connect() as conn:
                query = """
                    SELECT i.id_incidencia, e.nombre, i.tipo, i.descripcion, 
                           i.estado, i.fecha_reporte, i.solucion, i.fecha_resolucion
                    FROM incidencias i
                    JOIN espacios e ON i.id_espacio = e.id_espacio
                    WHERE 1=1
                """
                params = {}
                
                if estado:
                    query += " AND i.estado = :estado"
                    params["estado"] = estado
                
                if space_id:
                    query += " AND i.id_espacio = :space_id"
                    params["space_id"] = space_id
                
                query += " ORDER BY i.fecha_reporte DESC"
                
                result = conn.execute(text(query), params)
                
                incidents = []
                for row in result:
                    incidents.append({
                        "id": row[0],
                        "espacio": row[1],
                        "tipo": row[2],
                        "descripcion": row[3],
                        "estado": row[4],
                        "fecha_reporte": row[5].isoformat(),
                        "solucion": row[6],
                        "fecha_resolucion": row[7].isoformat() if row[7] else None
                    })
                
                return incidents
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "incid":
                return self.format_response("incid", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'report' in data or ('space' in data and 'tipo' in data and 'descripcion' in data):
                response = self.handle_report_incident(data)
            elif 'block' in data or ('incidencia' in data and 'inicio' in data and 'fin' in data):
                response = self.handle_apply_block(data)
            elif 'resolve' in data or ('incidencia' in data and 'solucion' in data):
                response = self.handle_resolve_incident(data)
            elif 'getall' in data or data == {}:
                response = self.handle_get_incidents(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("incid", response)
            
        except Exception as e:
            return self.format_response("incid", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[INCID] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[INCID] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[INCID] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[INCID] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[INCID] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de incidencias"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[INCID] Servicio de Incidencias iniciado en {self.host}:{self.port}")
            
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
                        print(f"[INCID] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[INCID] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de incidencias"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[INCID] Servicio de Incidencias detenido")

def main():
    """Función principal"""
    service = IncidentService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[INCID] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()