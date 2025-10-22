#!/usr/bin/env python3
"""
Script para iniciar todos los servicios del Sistema de Reservación UDP
"""
import subprocess
import time
import os
import sys
from pathlib import Path

def start_service(service_name, service_file, port):
    """Iniciar un servicio en un proceso separado"""
    try:
        print(f"Iniciando {service_name} en puerto {port}...")
        process = subprocess.Popen([
            sys.executable, service_file
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Esperar un poco para verificar que el servicio se inició correctamente
        time.sleep(1)
        
        if process.poll() is None:
            print(f"✓ {service_name} iniciado correctamente (PID: {process.pid})")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"✗ Error iniciando {service_name}: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"✗ Error iniciando {service_name}: {e}")
        return None

def main():
    """Función principal"""
    print("=== Sistema de Reservación UDP - Iniciando Servicios ===")
    
    # Cambiar al directorio del proyecto
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Lista de servicios a iniciar
    services = [
        ("Bus de Servicios", "services/service_bus.py", 5000),
        ("Servicio de Autenticación", "services/auth_service.py", 5001),
        ("Servicio de Usuarios", "services/user_service.py", 5002),
        ("Servicio de Espacios", "services/space_service.py", 5003),
        ("Servicio de Disponibilidad", "services/availability_service.py", 5004),
        ("Servicio de Reservas", "services/booking_service.py", 5005),
        ("Servicio de Incidencias", "services/incident_service.py", 5006),
        ("Servicio de Administración", "services/admin_service.py", 5007),
        ("Servicio de Notificaciones", "services/notification_service.py", 5008),
        ("Servicio de Reportes", "services/report_service.py", 5009)
    ]
    
    processes = []
    
    try:
        # Iniciar todos los servicios
        for service_name, service_file, port in services:
            process = start_service(service_name, service_file, port)
            if process:
                processes.append((service_name, process))
            time.sleep(0.5)  # Pequeña pausa entre servicios
        
        print(f"\n✓ {len(processes)} servicios iniciados correctamente")
        print("\nServicios activos:")
        for service_name, process in processes:
            print(f"  - {service_name} (PID: {process.pid})")
        
        print("\nPresiona Ctrl+C para detener todos los servicios...")
        
        # Mantener el script ejecutándose
        while True:
            time.sleep(1)
            
            # Verificar que todos los procesos sigan activos
            active_processes = []
            for service_name, process in processes:
                if process.poll() is None:
                    active_processes.append((service_name, process))
                else:
                    print(f"⚠ {service_name} se ha detenido inesperadamente")
            
            processes = active_processes
            
            if not processes:
                print("✗ Todos los servicios se han detenido")
                break
                
    except KeyboardInterrupt:
        print("\n\nDeteniendo todos los servicios...")
        
        # Terminar todos los procesos
        for service_name, process in processes:
            try:
                print(f"Deteniendo {service_name}...")
                process.terminate()
                process.wait(timeout=5)
                print(f"✓ {service_name} detenido")
            except subprocess.TimeoutExpired:
                print(f"⚠ {service_name} no respondió, forzando terminación...")
                process.kill()
            except Exception as e:
                print(f"✗ Error deteniendo {service_name}: {e}")
        
        print("\n✓ Todos los servicios han sido detenidos")

if __name__ == "__main__":
    main()
