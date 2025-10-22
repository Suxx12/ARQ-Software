#!/usr/bin/env python3
"""
Script para configurar la base de datos del Sistema de Reservación UDP
"""
import psycopg2
import os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def setup_database():
    """Configurar base de datos PostgreSQL"""
    try:
        print("🗄️  Configurando base de datos PostgreSQL...")
        
        # Configuración de conexión
        db_config = {
            'host': 'localhost',
            'port': 5432,
            'user': 'postgres',
            'password': 'password'  # Cambiar por tu contraseña
        }
        
        # Conectar a PostgreSQL
        print("Conectando a PostgreSQL...")
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Crear base de datos si no existe
        print("Creando base de datos 'reservas_udp'...")
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'reservas_udp'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute("CREATE DATABASE reservas_udp")
            print("✅ Base de datos creada exitosamente")
        else:
            print("ℹ️  La base de datos ya existe")
        
        # Cerrar conexión inicial
        cursor.close()
        conn.close()
        
        # Conectar a la nueva base de datos
        db_config['database'] = 'reservas_udp'
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Ejecutar script de inicialización (sin comandos psql)
        print("Ejecutando script de inicialización...")
        with open('database/init.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Dividir el script en comandos individuales y ejecutar solo los SQL
        sql_commands = []
        for line in sql_script.split('\n'):
            line = line.strip()
            if line and not line.startswith('--') and not line.startswith('\\'):
                sql_commands.append(line)
        
        # Ejecutar cada comando SQL
        for command in sql_commands:
            if command:
                try:
                    cursor.execute(command)
                except psycopg2.Error as e:
                    if "already exists" not in str(e):
                        print(f"⚠️  Advertencia: {e}")
        
        conn.commit()
        
        print("✅ Base de datos configurada exitosamente")
        
        # Verificar tablas creadas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        print("\n📋 Tablas creadas:")
        for table in tables:
            print(f"   • {table[0]}")
        
        # Insertar datos de prueba
        print("\n📝 Insertando datos de prueba...")
        
        # Verificar si ya hay datos
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Insertar usuario administrador de prueba
            cursor.execute("""
                INSERT INTO usuarios (rut, correo_institucional, nombre, tipo_usuario) 
                VALUES ('12345678-9', 'admin@udp.cl', 'Administrador Sistema', 'administrador')
                ON CONFLICT (rut) DO NOTHING
            """)
            
            # Insertar usuario estudiante de prueba
            cursor.execute("""
                INSERT INTO usuarios (rut, correo_institucional, nombre, tipo_usuario) 
                VALUES ('87654321-0', 'estudiante@udp.cl', 'Estudiante Prueba', 'estudiante')
                ON CONFLICT (rut) DO NOTHING
            """)
            
            conn.commit()
            print("✅ Usuarios de prueba creados")
        else:
            print("ℹ️  Los datos de prueba ya existen")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Base de datos configurada correctamente!")
        print("\n📋 Credenciales de prueba:")
        print("   • Administrador: 12345678-9 / admin@udp.cl")
        print("   • Estudiante: 87654321-0 / estudiante@udp.cl")
        
    except psycopg2.Error as e:
        print(f"❌ Error de base de datos: {e}")
        print("\n💡 Asegúrate de que:")
        print("   1. PostgreSQL esté instalado y ejecutándose")
        print("   2. La contraseña sea correcta")
        print("   3. El usuario 'postgres' tenga permisos para crear bases de datos")
        
    except FileNotFoundError:
        print("❌ No se encontró el archivo database/init.sql")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    setup_database()




