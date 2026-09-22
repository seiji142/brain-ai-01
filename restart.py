#!/usr/bin/env python3
"""Mata procesos en puerto 8000 y reinicia brain-ai-01."""
import subprocess
import time
import sys

print("Buscando procesos en puerto 8000...")
result = subprocess.run("netstat -ano | findstr :8000", shell=True, capture_output=True, text=True)
print(result.stdout or "No se encontraron procesos")

# Matar todos los procesos que usan puerto 8000
for line in result.stdout.splitlines():
    if "LISTENING" in line:
        pid = line.strip().split()[-1]
        print(f"Matiendo PID {pid}...")
        subprocess.run(f"taskkill /F /PID {pid}", shell=True)

time.sleep(2)

# Iniciar servidor
print("Iniciando brain-ai-01...")
subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "ai_architect.core.mcp_server:app",
     "--host", "127.0.0.1", "--port", "8000"],
    cwd=r"C:\Users\seiji\OneDrive\Documentos\Proyecto AI\brain-ai-01"
)
print("Servidor iniciado. Espera 3 segundos...")
time.sleep(3)
print("Listo!")
