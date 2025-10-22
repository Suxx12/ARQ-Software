"""
Bus de Servicios SOA - Sistema de Reservación UDP
Puerto: 5000
"""
import socket
import threading
import json
from typing import Dict, Any

class ServiceBus:
    """Bus de servicios para comunicación SOA"""
    
    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        self.services = {}  # Diccionario de servicios registrados
        self.running = False
        self.server_socket = None
        
        # Configuración de servicios
        self.service_config = {
            "auth": {"host": "localhost", "port": 5001},
            "user": {"host": "localhost", "port": 5002},
            "space": {"host": "localhost", "port": 5003},
            "avail": {"host": "localhost", "port": 5004},
            "book": {"host": "localhost", "port": 5005},
            "incid": {"host": "localhost", "port": 5006},
            "admin": {"host": "localhost", "port": 5007},
            "notif": {"host": "localhost", "port": 5008},
            "report": {"host": "localhost", "port": 5009}
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
    
    def format_response(self, service_code: str, data: Any) -> str:
        """Formatear respuesta según protocolo SOA"""
        json_data = json.dumps(data, ensure_ascii=False)
        service_code = service_code.ljust(5)[:5]
        message = service_code + json_data
        length_str = str(len(message)).zfill(5)
        
        return length_str + message
    
    def forward_to_service(self, service_code: str, data: Dict[str, Any]) -> str:
        """Reenviar mensaje a servicio específico"""
        try:
            if service_code not in self.service_config:
                return self.format_response(service_code, {"error": "Servicio no encontrado"})
            
            config = self.service_config[service_code]
            
            # Crear mensaje para el servicio
            message = self.format_response(service_code, data)
            
            # Conectar al servicio
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((config["host"], config["port"]))
                client_socket.sendall(message.encode('utf-8'))
                
                # Recibir respuesta
                response = client_socket.recv(4096).decode('utf-8')
                return response
                
        except Exception as e:
            return self.format_response(service_code, {"error": f"Error de comunicación: {str(e)}"})
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Manejar cliente conectado"""
        try:
            print(f"Conexión establecida desde {address}")
            
            while True:
                # Recibir mensaje
                message = client_socket.recv(4096).decode('utf-8')
                if not message:
                    break
                
                print(f"Mensaje recibido: {message[:50]}...")
                
                try:
                    # Parsear mensaje
                    service_code, data = self.parse_message(message)
                    print(f"Servicio: {service_code}, Datos: {data}")
                    
                    # Reenviar a servicio correspondiente
                    response = self.forward_to_service(service_code, data)
                    
                    # Enviar respuesta
                    client_socket.sendall(response.encode('utf-8'))
                    print(f"Respuesta enviada: {response[:50]}...")
                    
                except ValueError as e:
                    error_response = self.format_response("error", {"error": str(e)})
                    client_socket.sendall(error_response.encode('utf-8'))
                
        except Exception as e:
            print(f"Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            print(f"Conexión cerrada con {address}")
    
    def start(self):
        """Iniciar bus de servicios"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"Bus de servicios iniciado en {self.host}:{self.port}")
            
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
                        print(f"Error aceptando conexión: {e}")
                    
        except Exception as e:
            print(f"Error iniciando bus de servicios: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener bus de servicios"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("Bus de servicios detenido")

def main():
    """Función principal"""
    bus = ServiceBus()
    try:
        bus.start()
    except KeyboardInterrupt:
        print("\nDeteniendo bus de servicios...")
        bus.stop()

if __name__ == "__main__":
    main()





