-- Base de datos SQLite para Sistema de Reservación de Salas y Canchas - UDP

-- Tabla Usuarios
CREATE TABLE usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    rut VARCHAR(12) UNIQUE NOT NULL,
    correo_institucional VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    tipo_usuario VARCHAR(20) CHECK (tipo_usuario IN ('estudiante', 'funcionario', 'administrador')) NOT NULL,
    activo BOOLEAN DEFAULT 1,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla Espacios
CREATE TABLE espacios (
    id_espacio INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(10) CHECK (tipo IN ('sala', 'cancha')) NOT NULL,
    capacidad INTEGER NOT NULL,
    ubicacion VARCHAR(100),
    descripcion TEXT,
    activo BOOLEAN DEFAULT 1,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla Reservas
CREATE TABLE reservas (
    id_reserva INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    id_espacio INTEGER REFERENCES espacios(id_espacio),
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    estado VARCHAR(20) CHECK (estado IN ('pendiente', 'aprobada', 'rechazada', 'cancelada', 'bloqueo')) DEFAULT 'pendiente',
    motivo TEXT,
    fecha_solicitud DATETIME DEFAULT CURRENT_TIMESTAMP,
    recurrente BOOLEAN DEFAULT 0,
    patron_recurrencia VARCHAR(50),
    tipo_reserva VARCHAR(20) CHECK (tipo_reserva IN ('normal', 'bloqueo', 'incidencia')) DEFAULT 'normal',
    descripcion_incidencia TEXT,
    id_administrador_aprobador INTEGER REFERENCES usuarios(id_usuario),
    fecha_aprobacion DATETIME
);

-- Tabla Configuraciones
CREATE TABLE configuraciones (
    id_config INTEGER PRIMARY KEY AUTOINCREMENT,
    ventana_anticipacion_dias INTEGER DEFAULT 7,
    max_reservas_usuario INTEGER DEFAULT 1,
    duracion_max_horas INTEGER DEFAULT 4,
    hora_inicio TIME DEFAULT '08:00',
    hora_fin TIME DEFAULT '22:00',
    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla Incidencias
CREATE TABLE incidencias (
    id_incidencia INTEGER PRIMARY KEY AUTOINCREMENT,
    id_espacio INTEGER REFERENCES espacios(id_espacio),
    tipo VARCHAR(50) NOT NULL,
    descripcion TEXT NOT NULL,
    estado VARCHAR(20) CHECK (estado IN ('abierta', 'en_progreso', 'resuelta', 'cerrada')) DEFAULT 'abierta',
    fecha_reporte DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion DATETIME,
    id_usuario_reporte INTEGER REFERENCES usuarios(id_usuario),
    id_usuario_resuelve INTEGER REFERENCES usuarios(id_usuario),
    solucion TEXT
);

-- Tabla Auditoría
CREATE TABLE auditoria (
    id_auditoria INTEGER PRIMARY KEY AUTOINCREMENT,
    tabla_afectada VARCHAR(50) NOT NULL,
    accion VARCHAR(20) NOT NULL,
    id_registro INTEGER,
    datos_anteriores TEXT,
    datos_nuevos TEXT,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    fecha_accion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla Notificaciones
CREATE TABLE notificaciones (
    id_notificacion INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id_usuario),
    tipo VARCHAR(50) NOT NULL,
    mensaje TEXT NOT NULL,
    fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) DEFAULT 'enviada'
);

-- Tabla Plantillas de Notificación
CREATE TABLE plantillas_notificacion (
    id_plantilla INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo VARCHAR(50) UNIQUE NOT NULL,
    contenido TEXT NOT NULL,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insertar configuración inicial
INSERT INTO configuraciones (ventana_anticipacion_dias, max_reservas_usuario, duracion_max_horas, hora_inicio, hora_fin) 
VALUES (7, 1, 4, '08:00', '22:00');

-- Insertar usuario administrador inicial
INSERT INTO usuarios (rut, correo_institucional, nombre, tipo_usuario) 
VALUES ('12345678-9', 'admin@udp.cl', 'Administrador Sistema', 'administrador');

-- Insertar usuario estudiante de prueba
INSERT INTO usuarios (rut, correo_institucional, nombre, tipo_usuario) 
VALUES ('87654321-0', 'estudiante@udp.cl', 'Estudiante Prueba', 'estudiante');

-- Insertar algunos espacios de ejemplo
INSERT INTO espacios (nombre, tipo, capacidad, ubicacion, descripcion) VALUES 
('Sala A101', 'sala', 30, 'Edificio A', 'Sala de clases con proyector'),
('Sala B201', 'sala', 25, 'Edificio B', 'Sala de reuniones'),
('Cancha Futbol 1', 'cancha', 22, 'Complejo Deportivo', 'Cancha de futbol sintetica'),
('Cancha Basquetbol 1', 'cancha', 10, 'Gimnasio', 'Cancha de basquetbol cubierta');

-- Crear índices para optimizar consultas
CREATE INDEX idx_reservas_fecha_inicio ON reservas(fecha_inicio);
CREATE INDEX idx_reservas_fecha_fin ON reservas(fecha_fin);
CREATE INDEX idx_reservas_estado ON reservas(estado);
CREATE INDEX idx_reservas_id_usuario ON reservas(id_usuario);
CREATE INDEX idx_reservas_id_espacio ON reservas(id_espacio);
CREATE INDEX idx_usuarios_rut ON usuarios(rut);
CREATE INDEX idx_usuarios_correo ON usuarios(correo_institucional);
CREATE INDEX idx_espacios_tipo ON espacios(tipo);
CREATE INDEX idx_incidencias_estado ON incidencias(estado);
CREATE INDEX idx_auditoria_fecha ON auditoria(fecha_accion);

