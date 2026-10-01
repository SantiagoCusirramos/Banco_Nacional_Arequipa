# Guía de Instalación del Entorno de Desarrollo

Esta guía describe los pasos para clonar el repositorio y levantar el entorno de desarrollo local. Está dirigida a los 14 equipos de módulos y a los equipos de canales.

---

## Requisitos previos

Antes de clonar, verifica que tengas instalado:

| Herramienta | Versión mínima | Verificación |
|---|---|---|
| Git | 2.40+ | `git --version` |
| Python | 3.11+ | `python3 --version` |
| Node.js | 20.x LTS | `node --version` |
| npm | 10.x | `npm --version` |
| Docker | 24.x | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |

Si falta alguno, instálalo antes de continuar.

---

## Paso 1: Clonar el repositorio

```bash
git clone git@github.com:SantiagoCusirramos/Banco_Nacional_Arequipa.git
cd Banco_Nacional_Arequipa
