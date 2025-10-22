#!/usr/bin/env python3
"""
Servicio de Administración (ADMIN) - Sistema de Reservación UDP
Puerto: 5007
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

class AdminService:
    """Servicio de Administración según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5007):
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
    
    def handle_set_config(self, data: dict) -> dict:
        """Configurar parámetros operativos"""
        try:
            ventana_anticipacion = data.get('ventana_anticipacion', '')
            max_reservas = data.get('max_reservas', '')
            duracion_max = data.get('duracion_max', '')
            hora_inicio = data.get('hora_inicio', '')
            hora_fin = data.get('hora_fin', '')
            
            if not any([ventana_anticipacion, max_reservas, duracion_max, hora_inicio, hora_fin]):
                return {"error": "Al menos un parámetro debe ser proporcionado"}
            
            with self.engine.connect() as conn:
                # Verificar si existe configuración
                config_result = conn.execute(text("SELECT id_config FROM configuraciones LIMIT 1"))
                config_exists = config_result.fetchone()
                
                if config_exists:
                    # Actualizar configuración existente
                    updates = []
                    params = {}
                    
                    if ventana_anticipacion:
                        updates.append("ventana_anticipacion_dias = :ventana_anticipacion")
                        params["ventana_anticipacion"] = int(ventana_anticipacion)
                    
                    if max_reservas:
                        updates.append("max_reservas_usuario = :max_reservas")
                        params["max_reservas"] = int(max_reservas)
                    
                    if duracion_max:
                        updates.append("duracion_max_horas = :duracion_max")
                        params["duracion_max"] = int(duracion_max)
                    
                    if hora_inicio:
                        updates.append("hora_inicio = :hora_inicio")
                        params["hora_inicio"] = hora_inicio
                    
                    if hora_fin:
                        updates.append("hora_fin = :hora_fin")
                        params["hora_fin"] = hora_fin
                    
                    query = f"UPDATE configuraciones SET {', '.join(updates)}"
                    conn.execute(text(query), params)
                    
                else:
                    # Crear nueva configuración
                    conn.execute(text("""
                        INSERT INTO configuraciones (ventana_anticipacion_dias, max_reservas_usuario, 
                                                  duracion_max_horas, hora_inicio, hora_fin)
                        VALUES (:ventana_anticipacion, :max_reservas, :duracion_max, :hora_inicio, :hora_fin)
                    """), {
                        "ventana_anticipacion": int(ventana_anticipacion) if ventana_anticipacion else 7,
                        "max_reservas": int(max_reservas) if max_reservas else 1,
                        "duracion_max": int(duracion_max) if duracion_max else 4,
                        "hora_inicio": hora_inicio if hora_inicio else "08:00",
                        "hora_fin": hora_fin if hora_fin else "22:00"
                    })
                
                conn.commit()
                
                return {"configurado": True}
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_config(self, data: dict) -> dict:
        """Obtener configuración actual"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT ventana_anticipacion_dias, max_reservas_usuario, 
                           duracion_max_horas, hora_inicio, hora_fin
                    FROM configuraciones LIMIT 1
                """))
                
                config_row = result.fetchone()
                
                if config_row:
                    return {
                        "ventana_anticipacion": config_row[0],
                        "max_reservas": config_row[1],
                        "duracion_max": config_row[2],
                        "hora_inicio": str(config_row[3]),
                        "hora_fin": str(config_row[4])
                    }
                else:
                    # Configuración por defecto
                    return {
                        "ventana_anticipacion": 7,
                        "max_reservas": 1,
                        "duracion_max": 4,
                        "hora_inicio": "08:00",
                        "hora_fin": "22:00"
                    }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_audit(self, data: dict) -> dict:
        """Obtener historial de auditoría"""
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
                
                query += " ORDER BY fecha_accion DESC LIMIT 100"
                
                result = conn.execute(text(query), params)
                
                audit_log = []
                for row in result:
                    audit_log.append({
                        "accion": row[0],
                        "usuario": row[1],
                        "fecha": row[2].isoformat(),
                        "detalles": row[3]
                    })
                
                return audit_log
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_stats(self, data: dict) -> dict:
        """Obtener estadísticas del sistema"""
        try:
            with self.engine.connect() as conn:
                # Estadísticas de usuarios
                user_stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_usuarios,
                        SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as usuarios_activos,
                        SUM(CASE WHEN tipo_usuario = 'estudiante' THEN 1 ELSE 0 END) as estudiantes,
                        SUM(CASE WHEN tipo_usuario = 'funcionario' THEN 1 ELSE 0 END) as funcionarios,
                        SUM(CASE WHEN tipo_usuario = 'administrador' THEN 1 ELSE 0 END) as administradores
                    FROM usuarios
                """)).fetchone()
                
                # Estadísticas de espacios
                space_stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_espacios,
                        SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as espacios_activos,
                        SUM(CASE WHEN tipo = 'sala' THEN 1 ELSE 0 END) as salas,
                        SUM(CASE WHEN tipo = 'cancha' THEN 1 ELSE 0 END) as canchas
                    FROM espacios
                """)).fetchone()
                
                # Estadísticas de reservas
                booking_stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_reservas,
                        SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END) as pendientes,
                        SUM(CASE WHEN estado = 'aprobada' THEN 1 ELSE 0 END) as aprobadas,
                        SUM(CASE WHEN estado = 'rechazada' THEN 1 ELSE 0 END) as rechazadas,
                        SUM(CASE WHEN estado = 'cancelada' THEN 1 ELSE 0 END) as canceladas
                    FROM reservas
                """)).fetchone()
                
                return {
                    "usuarios": {
                        "total": user_stats[0],
                        "activos": user_stats[1],
                        "estudiantes": user_stats[2],
                        "funcionarios": user_stats[3],
                        "administradores": user_stats[4]
                    },
                    "espacios": {
                        "total": space_stats[0],
                        "activos": space_stats[1],
                        "salas": space_stats[2],
                        "canchas": space_stats[3]
                    },
                    "reservas": {
                        "total": booking_stats[0],
                        "pendientes": booking_stats[1],
                        "aprobadas": booking_stats[2],
                        "rechazadas": booking_stats[3],
                        "canceladas": booking_stats[4]
                    }
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "admin":
                return self.format_response("admin", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'config' in data or any(key in data for key in ['ventana_anticipacion', 'max_reservas', 'duracion_max']):
                response = self.handle_set_config(data)
            elif 'getconfig' in data or data == {}:
                response = self.handle_get_config(data)
            elif 'getaudit' in data or 'fecha' in data:
                response = self.handle_get_audit(data)
            elif 'getstats' in data or 'stats' in data:
                response = self.handle_get_stats(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("admin", response)
            
        except Exception as e:
            return self.format_response("admin", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[ADMIN] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[ADMIN] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[ADMIN] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[ADMIN] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[ADMIN] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de administración"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[ADMIN] Servicio de Administración iniciado en {self.host}:{self.port}")
            
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
                        print(f"[ADMIN] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[ADMIN] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de administración"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[ADMIN] Servicio de Administración detenido")

def main():
    """Función principal"""
    service = AdminService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[ADMIN] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()
