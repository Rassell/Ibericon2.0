# Gunicorn configuration file

# Timeout: tiempo máximo que un worker puede tomar para procesar una request
# Aumentado a 300 segundos (5 minutos) para operaciones largas como añadir torneos
timeout = 300

# Workers: número de procesos workers
# Render recomienda 2-4 workers por núcleo de CPU
workers = 2

# Threads: número de threads por worker
# Reducido a 2 para evitar problemas de SSL con PostgreSQL
threads = 2

# Worker class: usar threads para mejor manejo de I/O
worker_class = 'gthread'

# Bind: puerto donde escuchará (Render usa PORT env var)
bind = "0.0.0.0:3000"

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Graceful timeout
graceful_timeout = 120

# Keep alive
keepalive = 5
