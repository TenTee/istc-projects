# Prérequis

## Pour un essai sur un ordinateur

| Logiciel | Version | Où le trouver |
|---|---|---|
| Python | 3.11, 3.12 ou 3.13 | <https://www.python.org/downloads/> (Windows : cochez « Add Python to PATH ») |
| Node.js | 20 LTS ou plus récent | <https://nodejs.org> (version « LTS ») |
| Git | récent | <https://git-scm.com> |

Vérifiez dans un terminal (Windows : « Invite de commandes » ou « PowerShell » ; Mac : « Terminal ») :

```bash
python3 --version   # Windows : python --version
node --version
npm --version
git --version
```

## Pour la mise en ligne

| Élément | Recommandation |
|---|---|
| Serveur | Linux (Ubuntu 22.04/24.04 ou image Bitnami), 2 vCPU, 4 Go de RAM, 40 Go de disque minimum |
| Base de données | PostgreSQL 14 ou plus récent |
| Serveur web | Nginx (ou Apache sur Bitnami) en frontal, avec HTTPS |
| Nom de domaine | Ex. `smartcampus.exemple.cm` (interface) et éventuellement `api.smartcampus.exemple.cm` (API) |
| Certificat HTTPS | Let's Encrypt (gratuit) via `certbot`, ou l'outil `bncert-tool` sur Bitnami |
| Clés reCAPTCHA (facultatif) | <https://www.google.com/recaptcha/admin> : type **reCAPTCHA v2 « Je ne suis pas un robot »**, déclarer votre domaine. Vous obtenez une **clé du site** (publique) et une **clé secrète**. |

!!! info "Le frontend peut être hébergé ailleurs"
    L'interface (Next.js) peut tourner sur le même serveur ou sur un hébergeur spécialisé (Vercel…). Seule contrainte : son adresse doit être autorisée par le backend (voir `CORS_ALLOWED_ORIGINS` dans [Configuration](configuration.md)).
