#!/usr/bin/env python3
"""
Servicio de Reportes (REPRT) - Sistema de Reservación UDP
Puerto: 5009
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

class ReportService:
    """Servicio de Reportes según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5009):
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
    
    def handle_usage_report(self, data: dict) -> dict:
        """Generar reporte de uso"""
        try:
            fecha_inicio = data.get('fecha_inicio', '')
            fecha_fin = data.get('fecha_fin', '')
            
            if not all([fecha_inicio, fecha_fin]):
                return {"error": "Fecha de inicio y fin son requeridas"}
            
            with self.engine.connect() as conn:
                # Estadísticas generales de uso
                usage_stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_reservas,
                        SUM(CASE WHEN estado = 'aprobada' THEN 1 ELSE 0 END) as aprobadas,
                        SUM(CASE WHEN estado = 'rechazada' THEN 1 ELSE 0 END) as rechazadas,
                        SUM(CASE WHEN estado = 'cancelada' THEN 1 ELSE 0 END) as canceladas,
                        SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END) as pendientes
                    FROM reservas
                    WHERE fecha_solicitud BETWEEN :fecha_inicio AND :fecha_fin
                """), {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin
                }).fetchone()
                
                # Espacios más utilizados
                popular_spaces = conn.execute(text("""
                    SELECT e.nombre, COUNT(r.id_reserva) as total_reservas
                    FROM espacios e
                    LEFT JOIN reservas r ON e.id_espacio = r.id_espacio 
                        AND r.fecha_solicitud BETWEEN :fecha_inicio AND :fecha_fin
                        AND r.estado = 'aprobada'
                    GROUP BY e.id_espacio, e.nombre
                    ORDER BY total_reservas DESC
                    LIMIT 10
                """), {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin
                })
                
                espacios_mas_usados = []
                for row in popular_spaces:
                    espacios_mas_usados.append({
                        "espacio": row[0],
                        "reservas": row[1]
                    })
                
                # Calcular tasa de ocupación (simplificado)
                total_horas_disponibles = 14 * 30  # 14 horas por día * 30 días promedio
                total_horas_reservadas = usage_stats[1] * 2  # Asumiendo 2 horas promedio por reserva
                ocupacion = min(100, (total_horas_reservadas / total_horas_disponibles) * 100) if total_horas_disponibles > 0 else 0
                
                return {
                    "ocupacion": round(ocupacion, 2),
                    "total_reservas": usage_stats[0],
                    "aprobadas": usage_stats[1],
                    "rechazadas": usage_stats[2],
                    "canceladas": usage_stats[3],
                    "pendientes": usage_stats[4],
                    "espacios_mas_usados": espacios_mas_usados,
                    "periodo": {
                        "inicio": fecha_inicio,
                        "fin": fecha_fin
                    }
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_audit_report(self, data: dict) -> dict:
        """Generar reporte de auditoría"""
        try:
            fecha = data.get('fecha', '')
            fecha_inicio = data.get('fecha_inicio', '')
            fecha_fin = data.get('fecha_fin', '')
            
            with self.engine.connect() as conn:
                query = """
                    SELECT accion, usuario_id, fecha_accion, detalles
                    FROM auditoria
                    WHERE 1=1
                """
                params = {}
                
                if fecha:
                    query += " AND DATE(fecha_accion) = :fecha"
                    params["fecha"] = fecha
                elif fecha_inicio and fecha_fin:
                    query += " AND fecha_accion BETWEEN :fecha_inicio AND :fecha_fin"
                    params["fecha_inicio"] = fecha_inicio
                    params["fecha_fin"] = fecha_fin
                
                query += " ORDER BY fecha_accion DESC"
                
                result = conn.execute(text(query), params)
                
                audit_log = []
                for row in result:
                    audit_log.append({
                        "accion": row[0],
                        "usuario": row[1],
                        "fecha": row[2].isoformat(),
                        "detalles": row[3]
                    })
                
                return {
                    "audit_log": audit_log,
                    "total_registros": len(audit_log)
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_space_occupancy_report(self, data: dict) -> dict:
        """Generar reporte de ocupación por espacio"""
        try:
            fecha_inicio = data.get('fecha_inicio', '')
            fecha_fin = data.get('fecha_fin', '')
            
            if not all([fecha_inicio, fecha_fin]):
                return {"error": "Fecha de inicio y fin son requeridas"}
            
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        e.nombre,
                        e.tipo,
                        e.capacidad,
                        COUNT(r.id_reserva) as total_reservas,
                        SUM(CASE WHEN r.estado = 'aprobada' THEN 1 ELSE 0 END) as reservas_aprobadas,
                        SUM(CASE WHEN r.estado = 'aprobada' THEN 
                            (julianday(r.fecha_fin) - julianday(r.fecha_inicio)) * 24 
                            ELSE 0 END) as horas_ocupadas
                    FROM espacios e
                    LEFT JOIN reservas r ON e.id_espacio = r.id_espacio 
                        AND r.fecha_solicitud BETWEEN :fecha_inicio AND :fecha_fin
                    WHERE e.activo = 1
                    GROUP BY e.id_espacio, e.nombre, e.tipo, e.capacidad
                    ORDER BY horas_ocupadas DESC
                """), {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin
                })
                
                espacios_ocupacion = []
                for row in result:
                    # Calcular porcentaje de ocupación
                    dias_periodo = (datetime.fromisoformat(fecha_fin) - datetime.fromisoformat(fecha_inicio)).days
                    horas_disponibles = dias_periodo * 14  # 14 horas por día
                    porcentaje_ocupacion = (row[5] / horas_disponibles * 100) if horas_disponibles > 0 else 0
                    
                    espacios_ocupacion.append({
                        "espacio": row[0],
                        "tipo": row[1],
                        "capacidad": row[2],
                        "total_reservas": row[3],
                        "reservas_aprobadas": row[4],
                        "horas_ocupadas": round(row[5], 2),
                        "porcentaje_ocupacion": round(porcentaje_ocupacion, 2)
                    })
                
                return {
                    "espacios_ocupacion": espacios_ocupacion,
                    "periodo": {
                        "inicio": fecha_inicio,
                        "fin": fecha_fin
                    }
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_user_activity_report(self, data: dict) -> dict:
        """Generar reporte de actividad de usuarios"""
        try:
            fecha_inicio = data.get('fecha_inicio', '')
            fecha_fin = data.get('fecha_fin', '')
            
            if not all([fecha_inicio, fecha_fin]):
                return {"error": "Fecha de inicio y fin son requeridas"}
            
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        u.nombre,
                        u.tipo_usuario,
                        COUNT(r.id_reserva) as total_reservas,
                        SUM(CASE WHEN r.estado = 'aprobada' THEN 1 ELSE 0 END) as reservas_aprobadas,
                        SUM(CASE WHEN r.estado = 'rechazada' THEN 1 ELSE 0 END) as reservas_rechazadas,
                        SUM(CASE WHEN r.estado = 'cancelada' THEN 1 ELSE 0 END) as reservas_canceladas
                    FROM usuarios u
                    LEFT JOIN reservas r ON u.id_usuario = r.id_usuario 
                        AND r.fecha_solicitud BETWEEN :fecha_inicio AND :fecha_fin
                    WHERE u.activo = 1
                    GROUP BY u.id_usuario, u.nombre, u.tipo_usuario
                    HAVING total_reservas > 0
                    ORDER BY total_reservas DESC
                """), {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin
                })
                
                usuarios_actividad = []
                for row in result:
                    usuarios_actividad.append({
                        "usuario": row[0],
                        "tipo": row[1],
                        "total_reservas": row[2],
                        "aprobadas": row[3],
                        "rechazadas": row[4],
                        "canceladas": row[5]
                    })
                
                return {
                    "usuarios_actividad": usuarios_actividad,
                    "periodo": {
                        "inicio": fecha_inicio,
                        "fin": fecha_fin
                    }
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "report":
                return self.format_response("report", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'uso' in data or ('fecha_inicio' in data and 'fecha_fin' in data and 'tipo' not in data):
                response = self.handle_usage_report(data)
            elif 'audit' in data or 'fecha' in data:
                response = self.handle_audit_report(data)
            elif 'ocupacion' in data or ('fecha_inicio' in data and 'fecha_fin' in data and 'tipo' in data and data['tipo'] == 'ocupacion'):
                response = self.handle_space_occupancy_report(data)
            elif 'actividad' in data or ('fecha_inicio' in data and 'fecha_fin' in data and 'tipo' in data and data['tipo'] == 'actividad'):
                response = self.handle_user_activity_report(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("report", response)
            
        except Exception as e:
            return self.format_response("report", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[REPORT] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[REPORT] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[REPORT] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[REPORT] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[REPORT] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de reportes"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[REPORT] Servicio de Reportes iniciado en {self.host}:{self.port}")
            
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
                        print(f"[REPORT] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[REPORT] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de reportes"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[REPORT] Servicio de Reportes detenido")

def main():
    """Función principal"""
    service = ReportService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[REPORT] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()