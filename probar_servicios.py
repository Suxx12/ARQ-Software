#!/usr/bin/env python3
"""
Script de prueba para verificar que los servicios funcionen correctamente
"""
import socket
import json
import time

def test_service_connection(host, port, service_name):
    """Probar conexión a un servicio"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            print(f"[OK] {service_name} está ejecutándose en puerto {port}")
            return True
    except Exception as e:
        print(f"[ERROR] {service_name} no está disponible en puerto {port}: {e}")
        return False

def test_auth_service():
    """Probar servicio de autenticación"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect(('localhost', 5001))
            
            # Mensaje de prueba según protocolo SOA
            message = '00025auth {"rut":"12345678-9","pass":"test"}'
            s.sendall(message.encode('utf-8'))
            
            response = s.recv(4096).decode('utf-8')
            print(f"[OK] Servicio de Autenticación respondió: {response[:100]}...")
            return True
            
    except Exception as e:
        print(f"[ERROR] Error probando servicio de autenticación: {e}")
        return False

def test_user_service():
    """Probar servicio de usuarios"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect(('localhost', 5002))
            
            # Mensaje de prueba para obtener usuarios
            message = '00015user {"getall":true}'
            s.sendall(message.encode('utf-8'))
            
            response = s.recv(4096).decode('utf-8')
            print(f"[OK] Servicio de Usuarios respondió: {response[:100]}...")
            return True
            
    except Exception as e:
        print(f"[ERROR] Error probando servicio de usuarios: {e}")
        return False

def main():
    """Función principal de prueba"""
    print("=== Probando Servicios del Sistema de Reservación UDP ===\n")
    
    # Esperar un poco para que los servicios se inicien
    print("Esperando que los servicios se inicien...")
    time.sleep(3)
    
    # Probar conexiones básicas
    services = [
        ("Bus de Servicios", 5000),
        ("Servicio de Autenticación", 5001),
        ("Servicio de Usuarios", 5002),
        ("Servicio de Espacios", 5003),
        ("Servicio de Disponibilidad", 5004),
        ("Servicio de Reservas", 5005),
        ("Servicio de Incidencias", 5006),
        ("Servicio de Administración", 5007),
        ("Servicio de Notificaciones", 5008),
        ("Servicio de Reportes", 5009)
    ]
    
    print("\n1. Probando conexiones básicas:")
    active_services = 0
    for service_name, port in services:
        if test_service_connection('localhost', port, service_name):
            active_services += 1
    
    print(f"\nServicios activos: {active_services}/{len(services)}")
    
    # Probar funcionalidad específica
    print("\n2. Probando funcionalidad específica:")
    
    if test_auth_service():
        print("[OK] Autenticación funcionando")
    else:
        print("[ERROR] Problemas con autenticación")
    
    if test_user_service():
        print("[OK] Gestión de usuarios funcionando")
    else:
        print("[ERROR] Problemas con gestión de usuarios")
    
    print("\n=== Pruebas completadas ===")

if __name__ == "__main__":
    main()
