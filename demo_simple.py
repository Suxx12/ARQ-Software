#!/usr/bin/env python3
"""
Script Simplificado para Demostrar el Sistema
Solo servicios SOA + demo por terminal
"""
import subprocess
import time
import sys
import os

def iniciar_servicios_soa():
    """Iniciar todos los servicios SOA"""
    print("Iniciando Servicios SOA...")
    
    servicios = [
        ("Bus de Servicios", "services/service_bus.py", 5000),
        ("Autenticacion", "services/auth_service.py", 5001),
        ("Usuarios", "services/user_service.py", 5002),
        ("Espacios", "services/space_service.py", 5003),
        ("Disponibilidad", "services/availability_service.py", 5004),
        ("Reservas", "services/booking_service.py", 5005),
        ("Incidencias", "services/incident_service.py", 5006),
        ("Administracion", "services/admin_service.py", 5007),
        ("Notificaciones", "services/notification_service.py", 5008),
        ("Reportes", "services/report_service.py", 5009)
    ]
    
    procesos = []
    
    for nombre, archivo, puerto in servicios:
        try:
            print(f"   Iniciando {nombre}...")
            proceso = subprocess.Popen([sys.executable, archivo], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            procesos.append((nombre, proceso, puerto))
            time.sleep(0.5)
        except Exception as e:
            print(f"   [ERROR] Error iniciando {nombre}: {e}")
    
    print(f"\n[OK] {len(procesos)} servicios SOA iniciados")
    return procesos

def verificar_servicios(procesos):
    """Verificar que los servicios estén funcionando"""
    print("\nVerificando servicios...")
    
    import socket
    servicios_ok = 0
    
    for nombre, proceso, puerto in procesos:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect(('localhost', puerto))
                print(f"   [OK] {nombre} (puerto {puerto})")
                servicios_ok += 1
        except:
            print(f"   [ERROR] {nombre} (puerto {puerto}) - NO DISPONIBLE")
    
    print(f"\nServicios activos: {servicios_ok}/{len(procesos)}")
    return servicios_ok == len(procesos)

def ejecutar_demo():
    """Ejecutar demostración del sistema"""
    print("\nEjecutando demostracion del sistema...")
    try:
        resultado = subprocess.run([sys.executable, "demo_sistema.py"], 
                                 capture_output=True, text=True, timeout=60)
        print(resultado.stdout)
        if resultado.stderr:
            print("Errores:", resultado.stderr)
    except subprocess.TimeoutExpired:
        print("La demostracion tardo mas de 60 segundos")
    except Exception as e:
        print(f"Error ejecutando demo: {e}")

def main():
    """Función principal"""
    print("="*60)
    print("SISTEMA DE RESERVACION UDP - DEMOSTRACION")
    print("="*60)
    
    # Iniciar servicios
    procesos = iniciar_servicios_soa()
    
    # Esperar a que se inicien
    print("\nEsperando que los servicios se estabilicen...")
    time.sleep(3)
    
    # Verificar servicios
    if verificar_servicios(procesos):
        print("\n[OK] Todos los servicios estan funcionando correctamente!")
        
        # Ejecutar demo automáticamente
        ejecutar_demo()
    else:
        print("\n[ERROR] Algunos servicios no estan funcionando correctamente")
        print("   Revisa los logs de error arriba")
    
    print("\n" + "="*60)
    print("Sistema listo para demostracion!")
    print("="*60)
    print("\nPresiona Ctrl+C para detener todos los servicios")
    
    try:
        # Mantener el script ejecutándose
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nDeteniendo servicios...")
        for nombre, proceso, puerto in procesos:
            try:
                proceso.terminate()
                print(f"   [OK] {nombre} detenido")
            except:
                print(f"   [ERROR] Error deteniendo {nombre}")
        print("\nHasta luego!")

if __name__ == "__main__":
    main()
