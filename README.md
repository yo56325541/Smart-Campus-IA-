# SmartCampus AI – Backend API (Socle Applicatif & Sécurité)

Ce projet constitue le socle backend de la plateforme universitaire **SmartCampus AI**. Il gère le catalogue académique (formations, conditions d'admission, tarifs), les sessions de visite anonyme, les conversations, l'authentification sécurisée des candidats et l'administration de la plateforme.

---

## 1. Architecture & Technologies

- **Langage & Framework** : Python 3.13 / 3.14, FastAPI
- **Base de données relationnelle** : PostgreSQL (port natif 5433, **hors Docker**)
- **ORM & Migrations** : SQLAlchemy 2.0, Alembic, Psycopg 3
- **Sécurité & Authentification** : JWT (HS256 avec validation stricte), Argon2id (hachage et rehash adaptatif), sessions visiteurs par jeton opaque (SHA-256)
- **Protection & Anti-Abus** : Limiteur de débit multi-niveaux (In-Memory avec repli automatique, et support Redis pour environnements multi-workers)
- **Observabilité & Fiabilité** : Middleware `X-Request-ID`, journalisation structurée d'audit, sondes de santé (`/health/live`, `/health/ready`)
- **Validation des données** : Pydantic v2 avec contraintes numériques strictes (alignées sur `Numeric(10, 2)` PostgreSQL) et validation des années universitaires

---

## 2. Installation Locale (PostgreSQL Natif, Sans Docker)

> **Règle d'infrastructure** : La base de données PostgreSQL fonctionne **directement sur la machine hôte** (service natif Windows sur le port 5433). Elle n'est pas déployée sur Docker.

### Étape 1 : Initialisation de la base PostgreSQL
Exécutez le script d'initialisation en superutilisateur PostgreSQL (exécutable une seule fois) :
```powershell
psql -U postgres -h 127.0.0.1 -p 5433 -f db/setup.sql
```
Ce script crée de manière idempotente :
- L'utilisateur `smartcampus` avec le droit `CREATEDB`
- La base de données applicative `smartcampus`
- La base de données de test `smartcampus_test`

### Étape 2 : Environnement Python
```powershell
# Cloner / se placer dans le projet
cd C:\Users\Mohamed\Desktop\backend

# Créer et activer l'environnement virtuel
python -m venv .venv
.venv\Scripts\Activate.ps1

# Installer les dépendances
python -m pip install -r requirements.txt
```

### Étape 3 : Configuration (.env)
Copiez le modèle de configuration :
```powershell
copy .env.example .env
```
Éditez le fichier `.env` pour définir vos secrets :
- `ENVIRONMENT=dev` (ou `production`)
- `DATABASE_URL=postgresql+psycopg://smartcampus:smartcampus@127.0.0.1:5433/smartcampus?connect_timeout=5`
- `JWT_SECRET` (clé aléatoire d'au moins 32 caractères)
- `ADMIN_PASSWORD` (mot de passe robuste d'au moins 12 caractères)

### Étape 4 : Migrations de schéma (Alembic)
Appliquez les migrations vers la version la plus récente :
```powershell
python -m alembic upgrade head
```

Pour revenir en arrière (rollback) si nécessaire :
```powershell
python -m alembic downgrade base
```

### Étape 5 : Lancement du serveur
```powershell
python -m uvicorn app.main:app --reload --port 8000
```
- Documentation Swagger interactive : http://127.0.0.1:8000/docs
- Sonde de vivacité : http://127.0.0.1:8000/health/live
- Sonde de préparation (vérification DB) : http://127.0.0.1:8000/health/ready

---

## 3. Exécution des Tests

Les tests s'exécutent sur la base PostgreSQL dédiée `smartcampus_test` :

```powershell
# Exécution complète de la suite de tests (32 tests)
$env:TEST_DATABASE_URL="postgresql+psycopg://smartcampus:smartcampus@127.0.0.1:5433/smartcampus_test"
python -m pytest -v

# Exécution avec rapport de couverture de code
python -m pytest --cov=app --cov-report=term-missing
```

La suite de tests couvre :
1. Les flux nominaux visiteur → création conversation → inscription → rattachement (SA-29).
2. La concurrence réelle PostgreSQL (verrouillage de ligne `SELECT ... FOR UPDATE`, rattachement simultané par deux candidats, idempotence).
3. La sécurité JWT (tokens expirés, signatures corrompues, UUID invalides, rejet du rôle forgé).
4. Le blocage des comptes désactivés.
5. La protection du dernier administrateur actif contre la désactivation.
6. Le rate limiting multi-niveaux (IP, email, couple IP-email, Retry-After).
7. La validation des années académiques (ex: 2026-2027 validé, 2026-2028 refusé avec 422).
8. L'alignement numérique Pydantic / PostgreSQL `Numeric(10, 2)` (prévention des débordements).
9. La pagination au niveau SQL pour les utilisateurs admin et les conversations.
10. La purge des sessions anonymes expirées selon la politique de rétention.

---

## 4. Sécurité & Invariants Métier

### A. Rattachement Atomique et Concurrence (SA-29)
- **Problème résolu** : Le rattachement d'une session visiteur à un compte candidat est protégé contre les conditions de course via un verrouillage pessimiste PostgreSQL (`SELECT ... FOR UPDATE`).
- **Immuabilité** : Une session déjà liée à un candidat ne peut jamais être réassignée à un autre compte (conflit `409`). L'appel répété par le même candidat est idempotent (`200`).
- **Cohérence session / conversation** : Il est impossible qu'une conversation appartienne à un candidat tandis que sa session visiteur resterait orpheline. L'accès aux conversations liées par un visiteur anonyme ou un tiers est strictement refusé.

### B. Authentification & Rôles
- **Rôle authoritative** : Le rôle de l'utilisateur n'est jamais déduit du token JWT. Il est systématiquement relu en base de données pour chaque requête protégée.
- **Argon2id** : Hachage sécurisé des mots de passe avec vérification automatique de l'opportunité de rehash (`check_needs_rehash`) lors d'une authentification réussie si les paramètres de sécurité sont modifiés.

### C. Rate Limiting & Anti Brute-Force
- Limiteur glissant protégeant contre le password spraying et les attaques distribuées sur un compte cible.
- Support natif Redis via `REDIS_URL` pour les déploiements multi-instances, avec repli thread-safe en mémoire en environnement de développement.
- Prise en charge des reverse proxies de confiance (`TRUSTED_PROXIES` et `X-Forwarded-For`).

### D. Durée de Vie des Sessions & Rétention
- Expiration glissante de 24h bornée par une durée de vie absolue maximale de 30 jours (`SESSION_MAX_TTL_DAYS`).
- Endpoint d'administration `POST /admin/cleanup-sessions` et fonction de service pour purger les sessions orphelines expirées au-delà de 7 jours.

---

## 5. Endpoints de l'API

| Méthode | Route | Rôle requis | Description |
|---|---|---|---|
| `GET` | `/health/live` | Public | Sonde de vivacité (liveness probe) |
| `GET` | `/health/ready` | Public | Sonde de préparation vérifiant la connexion PostgreSQL |
| `POST` | `/sessions` | Public | Crée une session anonyme (retourne jeton opaque) |
| `GET` | `/sessions/me` | Visiteur | Consulte l'état de la session |
| `POST` | `/sessions/link` | Candidat | Lie atomiquement la session au candidat connecté |
| `POST` | `/auth/register` | Public | Inscription candidat (protégée par rate limit IP) |
| `POST` | `/auth/login` | Public | Connexion JSON (anti brute-force, `Retry-After`) |
| `GET` | `/auth/me` | Connecté | Profil de l'utilisateur connecté |
| `GET` | `/conversations` | Visiteur / Candidat | Liste paginée des conversations (`limit`, `offset`) |
| `POST` | `/conversations` | Visiteur / Candidat | Crée une conversation (rattachement automatique) |
| `GET` | `/conversations/{id}` | Propriétaire | Récupère une conversation spécifique |
| `GET` | `/programs` | Public | Catalogue des formations (filtres et recherche) |
| `GET` | `/programs/{slug}` | Public | Détails d'une formation (conditions et tarifs) |
| `POST` | `/programs` | Admin | Ajout d'une formation |
| `PATCH` | `/programs/{slug}` | Admin | Modification d'une formation |
| `DELETE` | `/programs/{slug}` | Admin | Désactivation logique d'une formation |
| `GET` | `/programs/{slug}/admission-conditions` | Public | Liste ordonnée des conditions d'admission |
| `POST` | `/programs/{slug}/admission-conditions` | Admin | Ajout d'une condition d'admission |
| `PATCH` | `/admission-conditions/{id}` | Admin | Mise à jour d'une condition |
| `DELETE` | `/admission-conditions/{id}` | Admin | Suppression d'une condition |
| `GET` | `/programs/{slug}/tariffs` | Public | Tarifs filtrés par année académique |
| `POST` | `/programs/{slug}/tariffs` | Admin | Ajout d'un tarif annuel |
| `PATCH` | `/tariffs/{id}` | Admin | Mise à jour d'un tarif |
| `DELETE` | `/tariffs/{id}` | Admin | Suppression d'un tarif |
| `GET` | `/admin/users` | Admin | Liste paginée des utilisateurs (`limit`, `offset`) |
| `POST` | `/admin/users` | Admin | Création d'un utilisateur par un admin |
| `PATCH` | `/admin/users/{id}` | Admin | Activation/désactivation (protection dernier admin) |
| `POST` | `/admin/cleanup-sessions` | Admin | Purge des sessions anonymes expirées |

---

## 6. Déploiement

### Déploiement Natif (Recommandé)
1. Configurez un service systemd ou Windows Service pour `uvicorn app.main:app --workers 4`.
2. Configurez un reverse proxy Nginx avec terminaison TLS (HTTPS) et transfert de l'en-tête `X-Forwarded-For`.
3. Ajoutez l'IP de votre reverse proxy dans `TRUSTED_PROXIES` dans `.env`.
4. Configurez un cron journalier appelant `/admin/cleanup-sessions` pour la rétention des données.

### Déploiement Conteneur de l'API (Docker Compose)
Pour conteneuriser l'API tout en conservant PostgreSQL sur la machine hôte :
```powershell
docker compose up -d --build
```
L'API communique directement avec l'instance PostgreSQL locale via `host.docker.internal:5433`.
