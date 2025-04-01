FROM python:3.9-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema y el cliente de ArgoCD
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64 \
    && chmod +x /usr/local/bin/argocd \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar los archivos necesarios al contenedor
COPY monitor_argocd.py /app/
COPY requirements.txt /app/
COPY .env /app/

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar el script
CMD ["python", "monitor_argocd.py"]º