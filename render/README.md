# Render CRM staging

This is a temporary all-in-one Render staging setup for testing the WIT Insurance CRM custom app on ERPNext/Frappe.

It is not intended for production.

## Render service settings

Create a new Render Web Service and use:

```text
Runtime: Docker
Branch: render-crm-staging
Dockerfile Path: render/Dockerfile
Build Command: blank
Start Command / Docker Command: blank
```

Add a paid persistent disk:

```text
Mount path: /var/data
Size: 30 GB minimum, 50 GB recommended
```

## Environment variables

Required:

```text
SITE_NAME=<your-service-name>.onrender.com
ADMIN_PASSWORD=<strong admin password>
MYSQL_ROOT_PASSWORD=<strong mysql password>
```

Recommended:

```text
FRAPPE_BRANCH=develop
PORT=10000
```

After the first boot, login as:

```text
User: Administrator
Password: value of ADMIN_PASSWORD
```

## What this does

On first boot, `render/start.sh` initializes MariaDB under `/var/data/mysql`, creates a Frappe bench under `/var/data/frappe-bench`, installs ERPNext from this repository, copies `custom_apps/wit_insurance` into the bench, creates the site, and installs both `erpnext` and `wit_insurance`.

On later boots it reuses the persistent disk.

## Important

The first boot can take a long time. Use a paid Render instance and a persistent disk. The free tier is not appropriate for ERPNext.
