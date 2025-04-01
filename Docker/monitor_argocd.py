import os
import subprocess
import time
import json
import requests
from dotenv import load_dotenv

# Cargar las variables desde el archivo .env
load_dotenv()

# Configuración del Webhook de Slack y credenciales de ArgoCD desde variables de entorno
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ARGOCD_USERNAME = os.getenv("ARGOCD_USERNAME", "admin")
ARGOCD_PASSWORD = os.getenv("ARGOCD_PASSWORD")

# Validar que las variables sensibles estén configuradas
if not SLACK_WEBHOOK_URL:
    raise ValueError("❌ La variable de entorno SLACK_WEBHOOK_URL no está configurada.")
if not ARGOCD_PASSWORD:
    raise ValueError("❌ La variable de entorno ARGOCD_PASSWORD no está configurada.")

# Función para enviar notificación a Slack
def send_slack_notification(app_name, status, attempts, action=""):
    # Crear un mensaje formateado como tabla
    message_text = (
        f"```\n"
        f"{'Aplicación':<20} {'Estado':<15} {'Intentos':<10}\n"
        f"{'-' * 50}\n"
        f"{app_name:<20} {status:<15} {attempts:<10}\n"
        f"{'-' * 50}\n"
        f"{action}\n"
        f"```"
    )

    # Crear el payload para Slack
    message = {
        "text": f"⚠️ *Estado de la aplicación:*",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message_text
                }
            }
        ]
    }

    # Enviar la notificación a Slack
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=message)
        response.raise_for_status()
        print(f"📩 Notificación enviada a Slack: {app_name} - {status}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al enviar notificación a Slack: {e}")

# Función para iniciar sesión en ArgoCD
def argocd_login():
    try:
        result = subprocess.run(
            ["argocd", "login", "localhost:8080", "--username", ARGOCD_USERNAME, "--password", ARGOCD_PASSWORD, "--insecure"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al autenticar en ArgoCD: {e}")
        print(f"Detalles del error: {e.stderr}")
        return False
    return True

# Función para obtener las aplicaciones de ArgoCD
def get_argocd_apps():
    try:
        result = subprocess.run(
            ["argocd", "app", "list", "--output", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        apps = json.loads(result.stdout)
        return apps
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al obtener la lista de aplicaciones: {e}")
        print(f"Detalles del error: {e.stderr}")
        return []

# Función para sincronizar aplicaciones
def sync_app(app_name):
    try:
        result = subprocess.run(
            ["argocd", "app", "sync", app_name],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"🔄 Se ejecutó 'argocd app sync' en {app_name}.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al sincronizar {app_name}: {e}")
        print(f"Detalles del error: {e.stderr}")

# Función para refrescar una aplicación
def refresh_app(app_name):
    try:
        result = subprocess.run(
            ["argocd", "app", "get", app_name, "--refresh"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al refrescar la aplicación {app_name}: {e}")
        print(f"Detalles del error: {e.stderr}")

# Función para desactivar el auto-sync
def disable_auto_sync(app_name):
    try:
        result = subprocess.run(
            ["argocd", "app", "set", app_name, "--sync-policy", "manual"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"⚙️ Auto-sync desactivado para {app_name}.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al desactivar el auto-sync para {app_name}: {e}")
        print(f"Detalles del error: {e.stderr}")

# Función para activar el auto-sync
def enable_auto_sync(app_name):
    try:
        result = subprocess.run(
            ["argocd", "app", "set", app_name, "--sync-policy", "automated"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"⚙️ Auto-sync activado para {app_name}.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al activar el auto-sync para {app_name}: {e}")
        print(f"Detalles del error: {e.stderr}")

# Función para realizar rollback de una aplicación
def rollback_app(app_name):
    try:
        result = subprocess.run(
            ["argocd", "app", "rollback", app_name],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"🔄 Se ejecutó rollback en la aplicación {app_name}.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al hacer rollback de la aplicación {app_name}: {e}")
        print(f"Detalles del error: {e.stderr}")
        return False

# Función para verificar si la aplicación está en estado Healthy después del rollback
def check_app_health(app_name):
    try:
        result = subprocess.run(
            ["argocd", "app", "get", app_name, "--output", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        app_info = json.loads(result.stdout)
        health_status = app_info[0].get('status', {}).get('health', {}).get('status', '')
        if health_status == 'Healthy':
            print(f"✅ La aplicación {app_name} está en estado Healthy después del rollback.")
            return True
        else:
            print(f"⚠️ La aplicación {app_name} aún no está Healthy. Estado actual: {health_status}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al verificar el estado de la aplicación {app_name}: {e}")
        print(f"Detalles del error: {e.stderr}")
        return False

# Función principal para monitorear el estado de las aplicaciones
attempts = {}

while True:
    if not argocd_login():
        print("❌ Falló la autenticación en ArgoCD. Saliendo...")
        break

    apps = get_argocd_apps()

    print("\n📋 Estado actual de las aplicaciones:")
    print(f"{'Aplicación':<20} {'Estado':<15} {'Intentos':<10}")
    print("-" * 50)

    for app in apps:
        app_name = app.get("metadata", {}).get("name", "Desconocido")

        # Realizar un refresh de la aplicación antes de verificar su estado
        refresh_app(app_name)

        # Obtener el estado actualizado de la aplicación
        status = app.get("status", {}).get("health", {}).get("status", "Unknown")
        sync_status = app.get("status", {}).get("sync", {}).get("status", "Unknown")  # Obtener el estado de sincronización

        # Inicializa los intentos para cada aplicación si no existen
        if app_name not in attempts:
            attempts[app_name] = 0

        # Verifica el estado de la aplicación y maneja las notificaciones
        if status == "Healthy" and sync_status == "Synced":
            # Solo imprime si la aplicación estaba previamente en un estado problemático
            print(f"{app_name:<20} {'Healthy':<15} {'-':<10}")
            if attempts[app_name] != 0:  # Si estaba pausada o con intentos, reinicia
                print(f"✅ {app_name} -- Healthy y Synced. Reiniciando monitoreo.")
                send_slack_notification(app_name, "Healthy", attempts[app_name], "La aplicación volvió a estar Healthy.")
                attempts[app_name] = 0  # Reinicia los intentos
        elif sync_status == "OutOfSync":
            print(f"{app_name:<20} {'OutOfSync':<15} {attempts[app_name]:<10}")

            # Intentar un sync forzado
            try:
                subprocess.run(
                    ["argocd", "app", "sync", app_name, "--force"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"✅ Sync forzado exitoso para {app_name}.")
                refresh_app(app_name)  # Refrescar el estado después del sync
            except subprocess.CalledProcessError as e:
                print(f"❌ Error al realizar el sync forzado para {app_name}.")
        elif status in ["Degraded", "Error"]:
            print(f"{app_name:<20} {status:<15} {attempts[app_name]:<10}")

            # Si la aplicación está pausada, no enviar más notificaciones
            if attempts[app_name] == -1:
                print(f"⏸️ {app_name} está pausada. Monitoreando cambios en su estado...")
                continue

            # Intentar desplegar hasta 3 veces
            if attempts[app_name] < 3:
                print(f"🔄 Intentando desplegar {app_name} ({attempts[app_name] + 1}/3)")
                try:
                    sync_app(app_name)
                    refresh_app(app_name)  # Refrescar el estado después del intento
                except subprocess.CalledProcessError as e:
                    print(f"❌ Error al intentar desplegar {app_name}: {e}")
                attempts[app_name] += 1
            else:
                # Pausar la aplicación después de 3 intentos fallidos
                print(f"⏸️ Pausando {app_name} después de 3 intentos fallidos.")
                disable_auto_sync(app_name)
                send_slack_notification(app_name, status, attempts[app_name], "La aplicación fue pausada después de 3 intentos fallidos.")
                attempts[app_name] = -1  # Marcar como pausada
        else:
            # Imprime el estado desconocido o no relevante
            print(f"{app_name:<20} {'Unknown':<15} {'-':<10}")

    print("-" * 50)
    # Espera 30 segundos antes de realizar el siguiente ciclo de verificación
    time.sleep(10)