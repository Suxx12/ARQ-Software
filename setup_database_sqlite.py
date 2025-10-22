#!/usr/bin/env python3
"""
Script para configurar la base de datos SQLite del Sistema de Reservación UDP
"""
import sqlite3
import os

def setup_database():
    """Configurar base de datos SQLite"""
    try:
        print("Configurando base de datos SQLite...")
        
        # Crear conexión a SQLite
        db_path = "reservas_udp_new.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Base de datos SQLite creada")
        
        # Ejecutar script de inicialización
        print("Ejecutando script de inicializacion...")
        with open('database/init_sqlite.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Adaptar el script para SQLite
        sql_script = sql_script.replace('SERIAL', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        sql_script = sql_script.replace('TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
        sql_script = sql_script.replace('ON CONFLICT', '-- ON CONFLICT')  # Comentar conflictos por ahora
        
        # Ejecutar el script
        cursor.executescript(sql_script)
        
        print("Base de datos configurada exitosamente")
        
        # Verificar tablas creadas
        cursor.execute("""
            SELECT name 
            FROM sqlite_master 
            WHERE type='table'
        """)
        tables = cursor.fetchall()
        
        print("\nTablas creadas:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Insertar datos de prueba
        print("\nInsertando datos de prueba...")
        
        # Verificar si ya hay datos
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Insertar usuario administrador de prueba
            cursor.execute("""
                INSERT OR IGNORE INTO usuarios (rut, correo_institucional, nombre, tipo_usuario) 
                VALUES ('12345678-9', 'admin@udp.cl', 'Administrador Sistema', 'administrador')
            """)
            
            # Insertar usuario estudiante de prueba
            cursor.execute("""
                INSERT OR IGNORE INTO usuarios (rut, correo_institucional, nombre, tipo_usuario) 
                VALUES ('87654321-0', 'estudiante@udp.cl', 'Estudiante Prueba', 'estudiante')
            """)
            
            # Insertar algunos espacios de prueba
            cursor.execute("""
                INSERT OR IGNORE INTO espacios (nombre, tipo, capacidad, ubicacion, descripcion) 
                VALUES ('Sala A101', 'sala', 30, 'Edificio A', 'Sala de clases con proyector')
            """)
            
            cursor.execute("""
                INSERT OR IGNORE INTO espacios (nombre, tipo, capacidad, ubicacion, descripcion) 
                VALUES ('Cancha Futbol 1', 'cancha', 22, 'Complejo Deportivo', 'Cancha de futbol sintetica')
            """)
            
            conn.commit()
            print("Datos de prueba creados")
        else:
            print("Los datos de prueba ya existen")
        
        cursor.close()
        conn.close()
        
        print("\nBase de datos configurada correctamente!")
        print("\nCredenciales de prueba:")
        print("   - Administrador: 12345678-9 / admin@udp.cl")
        print("   - Estudiante: 87654321-0 / estudiante@udp.cl")
        
    except FileNotFoundError:
        print("No se encontro el archivo database/init.sql")
        
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    setup_database()
