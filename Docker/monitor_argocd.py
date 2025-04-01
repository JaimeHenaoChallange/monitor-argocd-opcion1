import os
import subprocess
import json
import requests
from dotenv import load_dotenv

# Cargar las variables desde el archivo .env
load_dotenv()

# Configuración del Webhook de Slack y credenciales de ArgoCD desde variables de entorno
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ARGOCD_SERVER = os.getenv("ARGOCD_SERVER", "argocd-server.argocd.svc.cluster.local:443")
ARGOCD_USERNAME = os.getenv("ARGOCD_USERNAME", "admin")
ARGOCD_PASSWORD = os.getenv("ARGOCD_PASSWORD")

# Validar que las variables sensibles estén configuradas
if not SLACK_WEBHOOK_URL:
    raise ValueError("❌ La variable de entorno SLACK_WEBHOOK_URL no está configurada.")
if not ARGOCD_PASSWORD:
    raise ValueError("❌ La variable de entorno ARGOCD_PASSWORD no está configurada.")

# Función para enviar notificación a Slack
def send_slack_notification(app_name, status, attempts, action=""):
    message_text = (
        f"```\n"
        f"{'Aplicación':<20} {'Estado':<15} {'Intentos':<10}\n"
        f"{'-' * 50}\n"
        f"{app_name:<20} {status:<15} {attempts:<10}\n"
        f"{'-' * 50}\n"
        f"{action}\n"
        f"```"
    )
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
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=message)
        response.raise_for_status()
        print(f"📩 Notificación enviada a Slack: {app_name} - {status}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al enviar notificación a Slack: {e}")

# Función para iniciar sesión en ArgoCD
def argocd_login():
    try:
        subprocess.run(
            ["argocd", "login", ARGOCD_SERVER, "--username", ARGOCD_USERNAME, "--password", ARGOCD_PASSWORD, "--insecure"],
            capture_output=True, text=True, check=True
        )
        print("✅ Autenticación exitosa en ArgoCD.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al autenticar en ArgoCD: {e}")
        print(f"Detalles del error: {e.stderr}")
        return False

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

# Función principal para monitorear el estado de las aplicaciones
def monitor_apps():
    if not argocd_login():
        print("❌ Falló la autenticación en ArgoCD. Saliendo...")
        return

    apps = get_argocd_apps()

    print("\n📋 Estado actual de las aplicaciones:")
    print(f"{'Aplicación':<20} {'Estado':<15}")
    print("-" * 50)

    for app in apps:
        app_name = app.get("metadata", {}).get("name", "Desconocido")
        status = app.get("status", {}).get("health", {}).get("status", "Unknown")
        sync_status = app.get("status", {}).get("sync", {}).get("status", "Unknown")

        print(f"{app_name:<20} {status:<15}")

        if status != "Healthy" or sync_status != "Synced":
            send_slack_notification(app_name, status, 0, "La aplicación requiere atención.")

    print("-" * 50)

# Ejecutar el monitoreo
if __name__ == "__main__":
    monitor_apps()