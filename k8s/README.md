# Despliegue del backend BNA en el clúster EPIS (k3s)

Namespace: `2022223632`. Requiere la VPN WireGuard encendida (`sudo wg-quick up epis`).

```bash
export KUBECONFIG=~/.kube/epis-k3s.yaml
NS=2022223632
```

## 1. Construir la imagen del backend

```bash
cd backend
docker build -t bna-backend:latest .
```

## 2. Publicar la imagen donde el clúster pueda leerla

El clúster no ve tu Docker local. Hay que subir la imagen a un registro
accesible desde la red de la VPN. Opciones (confirmar con el equipo cuál existe):

- Un registro del laboratorio (p. ej. en 172.16.10.x). Etiquetar y empujar:
  `docker tag bna-backend:latest <registro>/bna-backend:latest && docker push <registro>/bna-backend:latest`
- Docker Hub / GHCR público, si está permitido.

Luego poner esa ruta en `k8s/03-backend.yaml` (campo `image:`), reemplazando
`PLACEHOLDER_IMAGE`.

## 3. Cargar el esquema de la base `bna`

El contenedor MySQL arranca vacío (solo crea la base `bna`). Cargar los scripts:

```bash
kubectl -n $NS exec -i deploy/mysql -- \
  mysql -uroot -p"$DB_PASSWORD" bna \
  < "backend/Infraestructura - BD/Trabajo_hecho/BD/99_bna_unificado.sql"
```

## 4. Aplicar los manifiestos

```bash
# Editar primero k8s/01-secret.yaml (passwords) y k8s/03-backend.yaml (image)
kubectl apply -n $NS -f k8s/01-secret.yaml
kubectl apply -n $NS -f k8s/02-mysql.yaml
kubectl apply -n $NS -f k8s/03-backend.yaml
kubectl apply -n $NS -f k8s/04-ingress.yaml
```

## 5. Verificar

```bash
kubectl -n $NS get pods,svc,ingress
kubectl -n $NS port-forward svc/backend 8000:8000   # luego abrir http://localhost:8000/health
```

## Notas

- La cuenta NO puede crear StatefulSet, DaemonSet ni CronJob; por eso MySQL
  va como Deployment + PVC.
- Para pruebas locales sin clúster: `docker compose` con MySQL, o levantar
  MySQL aparte y correr `uvicorn main:app` desde `backend/`.
