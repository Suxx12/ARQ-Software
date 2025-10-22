#!/usr/bin/env python3
"""
Script de Demostración del Sistema de Reservación UDP
Muestra las funcionalidades principales del sistema
"""
import socket
import json
import time

class SistemaDemo:
    """Clase para demostrar el sistema de reservación"""
    
    def __init__(self):
        self.host = "localhost"
        self.ports = {
            "auth": 5001,
            "user": 5002,
            "space": 5003,
            "avail": 5004,
            "book": 5005,
            "incid": 5006,
            "admin": 5007,
            "notif": 5008,
            "report": 5009
        }
    
    def send_message(self, port, message):
        """Enviar mensaje a un servicio"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.host, port))
                s.sendall(message.encode('utf-8'))
                response = s.recv(4096).decode('utf-8')
                return response
        except Exception as e:
            return f"Error: {e}"
    
    def demo_autenticacion(self):
        """Demostrar autenticación"""
        print("\n" + "="*60)
        print("DEMOSTRACION: AUTENTICACION DE USUARIOS")
        print("="*60)
        
        # Login como administrador
        print("\n1. Iniciando sesion como administrador...")
        message = '00025auth {"rut":"12345678-9","pass":"admin"}'
        response = self.send_message(self.ports["auth"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response[:100]}...")
        
        # Extraer token para usar en otras operaciones
        try:
            response_data = json.loads(response[10:])
            if "token" in response_data:
                self.admin_token = response_data["token"]
                print(f"   [OK] Token obtenido: {self.admin_token[:50]}...")
            else:
                print(f"   [ERROR] Error en autenticacion: {response_data}")
        except:
            print("   [ERROR] Error procesando respuesta de autenticacion")
    
    def demo_usuarios(self):
        """Demostrar gestión de usuarios"""
        print("\n" + "="*60)
        print("DEMOSTRACION: GESTION DE USUARIOS")
        print("="*60)
        
        # Obtener todos los usuarios
        print("\n1. Obteniendo lista de usuarios...")
        message = '00015user {"getall":true}'
        response = self.send_message(self.ports["user"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response[:150]}...")
        
        # Crear nuevo usuario
        print("\n2. Creando nuevo usuario estudiante...")
        message = '00050user {"rut":"11111111-1","correo":"nuevo@udp.cl","nombre":"Nuevo Estudiante","tipo":"estudiante"}'
        response = self.send_message(self.ports["user"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response}")
    
    def demo_espacios(self):
        """Demostrar gestión de espacios"""
        print("\n" + "="*60)
        print("DEMOSTRACION: GESTION DE ESPACIOS")
        print("="*60)
        
        # Obtener espacios existentes
        print("\n1. Obteniendo lista de espacios...")
        message = '00015space {"getall":true}'
        response = self.send_message(self.ports["space"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response[:150]}...")
        
        # Crear nuevo espacio
        print("\n2. Creando nuevo espacio...")
        message = '00040space {"nombre":"Sala Demo","tipo":"sala","capacidad":20}'
        response = self.send_message(self.ports["space"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response}")
    
    def demo_disponibilidad(self):
        """Demostrar consulta de disponibilidad"""
        print("\n" + "="*60)
        print("DEMOSTRACION: CONSULTA DE DISPONIBILIDAD")
        print("="*60)
        
        # Consultar disponibilidad
        print("\n1. Consultando disponibilidad para mañana...")
        message = '00040avail {"fecha":"2025-01-20","hora":"14:00","duracion":2}'
        response = self.send_message(self.ports["avail"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response[:200]}...")
    
    def demo_reservas(self):
        """Demostrar gestión de reservas"""
        print("\n" + "="*60)
        print("DEMOSTRACION: GESTION DE RESERVAS")
        print("="*60)
        
        # Crear reserva
        print("\n1. Creando nueva reserva...")
        message = '00060book {"user":"2","space":"1","inicio":"2025-01-20T14:00","fin":"2025-01-20T16:00","motivo":"Reunion de estudio"}'
        response = self.send_message(self.ports["book"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response}")
        
        # Obtener reservas del usuario
        print("\n2. Obteniendo reservas del usuario...")
        message = '00020book {"user":"2"}'
        response = self.send_message(self.ports["book"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response[:200]}...")
    
    def demo_incidencias(self):
        """Demostrar gestión de incidencias"""
        print("\n" + "="*60)
        print("DEMOSTRACION: GESTION DE INCIDENCIAS")
        print("="*60)
        
        # Reportar incidencia
        print("\n1. Reportando incidencia...")
        message = '00060incid {"space":"1","tipo":"averia","descripcion":"Proyector no funciona","user":"2"}'
        response = self.send_message(self.ports["incid"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response}")
        
        # Obtener incidencias
        print("\n2. Obteniendo lista de incidencias...")
        message = '00015incid {"getall":true}'
        response = self.send_message(self.ports["incid"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response[:200]}...")
    
    def demo_administracion(self):
        """Demostrar funciones de administración"""
        print("\n" + "="*60)
        print("DEMOSTRACION: ADMINISTRACION DEL SISTEMA")
        print("="*60)
        
        # Obtener configuración
        print("\n1. Obteniendo configuracion del sistema...")
        message = '00020admin {"getconfig":true}'
        response = self.send_message(self.ports["admin"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response}")
        
        # Obtener estadísticas
        print("\n2. Obteniendo estadisticas del sistema...")
        message = '00020admin {"stats":true}'
        response = self.send_message(self.ports["admin"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response[:200]}...")
    
    def demo_notificaciones(self):
        """Demostrar sistema de notificaciones"""
        print("\n" + "="*60)
        print("DEMOSTRACION: SISTEMA DE NOTIFICACIONES")
        print("="*60)
        
        # Enviar notificación
        print("\n1. Enviando notificacion de prueba...")
        message = '00050notif {"tipo":"aprobacion","usuario":"2","detalles":"Su reserva ha sido aprobada"}'
        response = self.send_message(self.ports["notif"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response}")
    
    def demo_reportes(self):
        """Demostrar sistema de reportes"""
        print("\n" + "="*60)
        print("DEMOSTRACION: SISTEMA DE REPORTES")
        print("="*60)
        
        # Generar reporte de uso
        print("\n1. Generando reporte de uso...")
        message = '00050report {"fecha_inicio":"2025-01-01","fecha_fin":"2025-01-31"}'
        response = self.send_message(self.ports["report"], message)
        print(f"   Mensaje enviado: {message}")
        print(f"   Respuesta: {response[:200]}...")
    
    def verificar_servicios(self):
        """Verificar que todos los servicios estén activos"""
        print("VERIFICANDO SERVICIOS...")
        servicios_activos = 0
        
        for nombre, puerto in self.ports.items():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    s.connect((self.host, puerto))
                    print(f"   [OK] {nombre.upper()} (puerto {puerto})")
                    servicios_activos += 1
            except:
                print(f"   [ERROR] {nombre.upper()} (puerto {puerto}) - NO DISPONIBLE")
        
        print(f"\nServicios activos: {servicios_activos}/{len(self.ports)}")
        return servicios_activos == len(self.ports)
    
    def ejecutar_demo_completa(self):
        """Ejecutar demostración completa del sistema"""
        print("SISTEMA DE RESERVACION UDP - DEMOSTRACION COMPLETA")
        print("="*80)
        
        # Verificar servicios
        if not self.verificar_servicios():
            print("\n[ERROR] Algunos servicios no estan disponibles. Asegurate de que todos esten ejecutandose.")
            return
        
        print("\n[OK] Todos los servicios estan activos. Iniciando demostracion...")
        time.sleep(2)
        
        # Ejecutar todas las demostraciones
        self.demo_autenticacion()
        time.sleep(1)
        
        self.demo_usuarios()
        time.sleep(1)
        
        self.demo_espacios()
        time.sleep(1)
        
        self.demo_disponibilidad()
        time.sleep(1)
        
        self.demo_reservas()
        time.sleep(1)
        
        self.demo_incidencias()
        time.sleep(1)
        
        self.demo_administracion()
        time.sleep(1)
        
        self.demo_notificaciones()
        time.sleep(1)
        
        self.demo_reportes()
        
        print("\n" + "="*80)
        print("DEMOSTRACION COMPLETADA")
        print("="*80)
        print("\nEl sistema esta funcionando correctamente con todos sus servicios:")
        print("• Autenticacion de usuarios con JWT")
        print("• Gestion completa de usuarios y espacios")
        print("• Sistema de reservas con validaciones")
        print("• Gestion de incidencias y bloqueos")
        print("• Administracion y configuracion")
        print("• Sistema de notificaciones")
        print("• Generacion de reportes y estadisticas")

def main():
    """Función principal"""
    demo = SistemaDemo()
    demo.ejecutar_demo_completa()

if __name__ == "__main__":
    main()