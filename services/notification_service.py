#!/usr/bin/env python3
"""
Servicio de Notificaciones (NOTIF) - Sistema de Reservación UDP
Puerto: 5008
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

class NotificationService:
    """Servicio de Notificaciones según especificación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5008):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        
        # Configuración de base de datos
        DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./reservas_udp.db')
        self.engine = create_engine(DATABASE_URL)
        
        # Plantillas de notificación por defecto
        self.default_templates = {
            "aprobacion": "Su reserva ha sido aprobada. Detalles: {detalles}",
            "rechazo": "Su reserva ha sido rechazada. Motivo: {motivo}",
            "cancelacion": "Su reserva ha sido cancelada. Detalles: {detalles}",
            "bloqueo": "Se ha aplicado un bloqueo que afecta su reserva. Detalles: {detalles}",
            "recordatorio": "Recordatorio: Tiene una reserva programada para {fecha_hora}"
        }
    
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
    
    def handle_send_notification(self, data: dict) -> dict:
        """Enviar notificación"""
        try:
            tipo = data.get('tipo', '')
            reserva_id = data.get('reserva', '')
            usuario_id = data.get('usuario', '')
            detalles = data.get('detalles', '')
            
            if not all([tipo, usuario_id]):
                return {"error": "Tipo y usuario son requeridos"}
            
            with self.engine.connect() as conn:
                # Obtener información del usuario
                user_result = conn.execute(text("""
                    SELECT correo_institucional, nombre FROM usuarios WHERE id_usuario = :user_id
                """), {"user_id": usuario_id})
                
                user_row = user_result.fetchone()
                if not user_row:
                    return {"error": "Usuario no encontrado"}
                
                email = user_row[0]
                nombre = user_row[1]
                
                # Obtener información de la reserva si se proporciona
                reserva_info = ""
                if reserva_id:
                    reserva_result = conn.execute(text("""
                        SELECT r.fecha_inicio, r.fecha_fin, e.nombre, r.motivo
                        FROM reservas r
                        JOIN espacios e ON r.id_espacio = e.id_espacio
                        WHERE r.id_reserva = :reserva_id
                    """), {"reserva_id": reserva_id})
                    
                    reserva_row = reserva_result.fetchone()
                    if reserva_row:
                        reserva_info = f"Espacio: {reserva_row[2]}, Fecha: {reserva_row[0]} - {reserva_row[1]}, Motivo: {reserva_row[3]}"
                
                # Obtener plantilla
                template_result = conn.execute(text("""
                    SELECT contenido FROM plantillas_notificacion WHERE tipo = :tipo
                """), {"tipo": tipo})
                
                template_row = template_result.fetchone()
                if template_row:
                    template = template_row[0]
                else:
                    template = self.default_templates.get(tipo, "Notificación del sistema: {detalles}")
                
                # Formatear mensaje
                mensaje = template.format(
                    nombre=nombre,
                    detalles=detalles or reserva_info,
                    fecha_hora=reserva_info
                )
                
                # Registrar notificación en la base de datos
                conn.execute(text("""
                    INSERT INTO notificaciones (usuario_id, tipo, mensaje, fecha_envio, estado)
                    VALUES (:user_id, :tipo, :mensaje, :fecha_envio, 'enviada')
                """), {
                    "user_id": usuario_id,
                    "tipo": tipo,
                    "mensaje": mensaje,
                    "fecha_envio": datetime.now()
                })
                
                conn.commit()
                
                # En un sistema real, aquí se enviaría el email
                # Por ahora solo simulamos el envío
                print(f"[NOTIF] Email enviado a {email}: {mensaje}")
                
                return {
                    "enviado": True,
                    "email": email,
                    "mensaje": mensaje
                }
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_set_template(self, data: dict) -> dict:
        """Configurar plantilla de notificación"""
        try:
            tipo = data.get('tipo', '')
            texto = data.get('texto', '')
            
            if not all([tipo, texto]):
                return {"error": "Tipo y texto son requeridos"}
            
            valid_types = ['aprobacion', 'rechazo', 'cancelacion', 'bloqueo', 'recordatorio']
            if tipo not in valid_types:
                return {"error": f"Tipo inválido. Tipos válidos: {valid_types}"}
            
            with self.engine.connect() as conn:
                # Verificar si la plantilla existe
                template_result = conn.execute(text("""
                    SELECT id FROM plantillas_notificacion WHERE tipo = :tipo
                """), {"tipo": tipo})
                
                if template_result.fetchone():
                    # Actualizar plantilla existente
                    conn.execute(text("""
                        UPDATE plantillas_notificacion SET contenido = :texto WHERE tipo = :tipo
                    """), {"texto": texto, "tipo": tipo})
                else:
                    # Crear nueva plantilla
                    conn.execute(text("""
                        INSERT INTO plantillas_notificacion (tipo, contenido, fecha_creacion)
                        VALUES (:tipo, :texto, :fecha_creacion)
                    """), {
                        "tipo": tipo,
                        "texto": texto,
                        "fecha_creacion": datetime.now()
                    })
                
                conn.commit()
                
                return {"configurado": True}
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def handle_get_notifications(self, data: dict) -> dict:
        """Obtener notificaciones de un usuario"""
        try:
            usuario_id = data.get('usuario', '')
            
            if not usuario_id:
                return {"error": "ID de usuario es requerido"}
            
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT tipo, mensaje, fecha_envio, estado
                    FROM notificaciones
                    WHERE usuario_id = :user_id
                    ORDER BY fecha_envio DESC
                    LIMIT 50
                """), {"user_id": usuario_id})
                
                notifications = []
                for row in result:
                    notifications.append({
                        "tipo": row[0],
                        "mensaje": row[1],
                        "fecha_envio": row[2].isoformat(),
                        "estado": row[3]
                    })
                
                return notifications
                
        except Exception as e:
            return {"error": f"Error interno: {str(e)}"}
    
    def process_message(self, message: str) -> str:
        """Procesar mensaje recibido"""
        try:
            service_code, data = self.parse_message(message)
            
            if service_code != "notif":
                return self.format_response("notif", {"error": "Servicio incorrecto"})
            
            # Determinar acción basada en los datos
            if 'send' in data or ('tipo' in data and 'usuario' in data):
                response = self.handle_send_notification(data)
            elif 'plantilla' in data or ('tipo' in data and 'texto' in data):
                response = self.handle_set_template(data)
            elif 'getnotifications' in data or ('usuario' in data and 'action' in data and data['action'] == 'get'):
                response = self.handle_get_notifications(data)
            else:
                response = {"error": "Acción no reconocida"}
            
            return self.format_response("notif", response)
            
        except Exception as e:
            return self.format_response("notif", {"error": str(e)})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"[NOTIF] Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"[NOTIF] Mensaje recibido: {message[:50]}...")
                
                # Procesar mensaje
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.sendall(response.encode('utf-8'))
                print(f"[NOTIF] Respuesta enviada: {response[:50]}...")
                
        except Exception as e:
            print(f"[NOTIF] Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"[NOTIF] Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar servicio de notificaciones"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"[NOTIF] Servicio de Notificaciones iniciado en {self.host}:{self.port}")
            
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
                        print(f"[NOTIF] Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"[NOTIF] Error iniciando servicio: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener servicio de notificaciones"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[NOTIF] Servicio de Notificaciones detenido")

def main():
    """Función principal"""
    service = NotificationService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[NOTIF] Deteniendo servicio...")
        service.stop()

if __name__ == "__main__":
    main()