# Membre 2 — Data Engineer / Base de données

> **Projet :** SmartCampus AI — Socle Technique  
> **Rôle :** Data Engineer / Base de données  
> **Epics couverts :** SA-10 (6 tâches) · SA-23 (1 tâche)  
> **Total :** 7 tâches (100% Réalisées)

---

## 1. Récapitulatif des tâches

| Clé   | Tâche                                                               | Story | Epic  | Statut |
|-------|---------------------------------------------------------------------|-------|-------|:------:|
| SA-12 | Concevoir les tables du catalogue académique                        | SA-11 | SA-10 | ✅ Terminé |
| SA-13 | Concevoir les tables des utilisateurs et des candidatures           | SA-11 | SA-10 | ✅ Terminé |
| SA-14 | Concevoir les tables de gestion des documents et de synchronisation | SA-11 | SA-10 | ✅ Terminé |
| SA-17 | Créer les tables et les relations de la base de données             | SA-15 | SA-10 | ✅ Terminé |
| SA-18 | Alimenter la base avec des données de démonstration                 | SA-15 | SA-10 | ✅ Terminé |
| SA-22 | Vérifier le fonctionnement et la fiabilité des API                  | SA-19 | SA-10 | ✅ Terminé |
| SA-26 | Mettre en place la mémoire temporaire des conversations             | SA-24 | SA-23 | ✅ Terminé |

---

## 2. Tables conçues et implémentées

### SA-12 — Catalogue académique

#### Table `programs`
Catalogue des formations proposées par les institutions (IIT / ISB).
- **Colonnes :** `id` (UUID PK), `slug` (VARCHAR(120) UNIQUE), `institution` (ENUM `IIT`, `ISB`), `level` (VARCHAR(50)), `name` (VARCHAR(200)), `description` (TEXT), `duration_years` (INT), `language` (VARCHAR(50)), `careers` (TEXT), `is_active` (BOOLEAN).
- **Relations :** 1→N vers `admission_conditions`, `tariffs`, `specialties`, `courses`, `applications`.

#### Table `specialties`
Spécialités rattachées aux formations (ex: Génie Logiciel, Cybersécurité & Cloud, IA & Data Science).
- **Colonnes :** `id` (UUID PK), `program_id` (FK → `programs.id` CASCADE), `name` (VARCHAR(150)), `code` (VARCHAR(50) INDEX), `description` (TEXT), `is_active` (BOOLEAN).
- **Relations :** N→1 vers `programs`, 1→N vers `courses`.

#### Table `courses`
Matières enseignées des programmes d'études (syllabus, crédits ECTS, volume horaire).
- **Colonnes :** `id` (UUID PK), `program_id` (FK → `programs.id` CASCADE), `specialty_id` (FK → `specialties.id` SET NULL), `code` (VARCHAR(30) INDEX), `name` (VARCHAR(200)), `semester` (VARCHAR(10)), `credits_ects` (NUMERIC(4,1)), `coefficient` (NUMERIC(4,2)), `hours_lectures` (INT), `hours_tutorials` (INT), `description` (TEXT).
- **Relations :** N→1 vers `programs`, N→1 vers `specialties`.

#### Table `admission_conditions`
Conditions d'admission rattachées à chaque programme.
- **Colonnes :** `id` (UUID PK), `program_id` (FK → `programs.id` CASCADE), `title` (VARCHAR(200)), `description` (TEXT), `required_diploma` (VARCHAR(120)), `min_average` (NUMERIC(4,2)), `position` (INT).

#### Table `tariffs`
Tarifs par programme et par année universitaire.
- **Colonnes :** `id` (UUID PK), `program_id` (FK → `programs.id` CASCADE), `academic_year` (VARCHAR(9)), `amount` (NUMERIC(10,2)), `registration_fee` (NUMERIC(10,2)), `currency` (VARCHAR(3)), `payment_terms` (TEXT).
- **Contrainte unique :** `(program_id, academic_year)` → `uq_tariffs_program_academic_year`.

---

### SA-13 — Utilisateurs, candidatures, profils et entretiens

#### Table `users`
Comptes utilisateurs (candidats, administrateurs, direction et responsables pédagogiques/admissions).
- **Colonnes :** `id` (UUID PK), `email` (VARCHAR(255) UNIQUE), `password_hash` (VARCHAR(255) Argon2id), `full_name` (VARCHAR(120)), `role` (ENUM `admin`, `candidat`, `responsable_academique_iit`, `responsable_academique_isb`, `responsable_entretien`, `direction`), `is_active` (BOOLEAN), `created_at` (TIMESTAMPTZ).
- **Relations :** 1→1 vers `academic_profiles`, 1→N vers `applications`, `documents`, `equivalences`.

##### Matrice des Rôles & Permissions (Projet IA Générative 2026-2027) :
1. **Responsable académique IIT (`responsable_academique_iit`) :**
   - *Mission :* Supervise les informations et recommandations concernant les formations proposées par l'IIT.
   - *Prérogatives :* Consulter les candidats orientés vers l'IIT ; accéder à leur profil et aux recommandations générées ; vérifier la cohérence de l'orientation proposée ; consulter les résultats du QCM ; confirmer ou ajuster une recommandation académique ; gérer les informations relatives aux formations IIT utilisées par le système ; consulter les statistiques d'intérêt et d'orientation vers les différents parcours.
2. **Responsable académique ISB (`responsable_academique_isb`) :**
   - *Mission :* Supervise les informations et recommandations concernant les formations proposées par l'ISB.
   - *Prérogatives :* Consulter les candidats orientés vers l'ISB ; accéder à leur profil et aux recommandations générées ; vérifier la cohérence de l'orientation proposée ; consulter les résultats du QCM ; confirmer ou ajuster une recommandation académique ; gérer les informations relatives aux formations ISB utilisées par le système ; consulter les statistiques d'intérêt et d'orientation vers les différents parcours.
3. **Responsable entretien (`responsable_entretien`) :**
   - *Mission :* Organise et réalise les entretiens des candidats préinscrits.
   - *Prérogatives :* Consulter les candidats prêts pour un entretien ; accéder au résumé de leur parcours conversationnel, à leur profil et à la formation recommandée ; consulter le QCM généré automatiquement et les réponses du candidat ; disposer d'une synthèse des points à approfondir pendant l'entretien ; définir ou valider un rendez-vous ; envoyer une invitation ; saisir le résultat et les observations de l'entretien ; demander un complément d'information ou transmettre le dossier à l'étape suivante.
4. **Direction (`direction`) :**
   - *Mission :* Supervise globalement le processus d'orientation, de préinscription et de conversion des candidats.
   - *Prérogatives :* Consulter un tableau de bord global ; suivre le nombre de conversations, orientations, préinscriptions, entretiens et inscriptions ; analyser les formations les plus demandées ; comparer les orientations IIT/ISB ; suivre les taux de transformation visiteur → préinscription → entretien → inscription ; consulter les indicateurs de performance du système agentique ; identifier les dossiers en attente ou abandonnés ; accéder à des statistiques et rapports d'aide à la décision.
5. **Administrateur (`admin`) :** Administration technique globale, gestion des utilisateurs et supervision transversale.
6. **Candidat (`candidat`) :** Exploration des formations, dialogue d'orientation avec le conseiller IA, soumission de candidature, dépôt de justificatifs et consultation de ses résultats.

#### Table `academic_profiles`
Profil académique détaillé du candidat (cursus antérieur, bac, mentions).
- **Colonnes :** `id` (UUID PK), `user_id` (FK → `users.id` CASCADE UNIQUE), `bac_section` (VARCHAR(100)), `bac_year` (INT), `bac_average` (NUMERIC(4,2)), `highest_diploma` (VARCHAR(150)), `graduation_institution` (VARCHAR(200)), `graduation_year` (INT), `notes` (TEXT), `created_at` / `updated_at` (TIMESTAMPTZ).
- **Contrainte unique :** 1 seul profil académique par compte candidat.

#### Table `equivalences`
Demandes d'équivalence de diplômes ou de crédits pour admission en cycle supérieur.
- **Colonnes :** `id` (UUID PK), `user_id` (FK → `users.id` CASCADE), `target_program_id` (FK → `programs.id` CASCADE), `source_diploma` (VARCHAR(200)), `source_institution` (VARCHAR(200)), `source_country` (VARCHAR(100)), `requested_level` (VARCHAR(50)), `status` (ENUM `pending`, `under_review`, `approved`, `rejected`), `decision_notes` (TEXT), `reviewed_by` (FK → `users.id` SET NULL), `created_at` / `updated_at` (TIMESTAMPTZ).

#### Table `applications`
Dossiers de candidature à une formation.
- **Colonnes :** `id` (UUID PK), `user_id` (FK → `users.id` CASCADE), `program_id` (FK → `programs.id` CASCADE), `academic_year` (VARCHAR(9)), `status` (ENUM `draft`, `submitted`, `under_review`, `accepted`, `rejected`), `notes` (TEXT), `created_at` / `updated_at` (TIMESTAMPTZ).
- **Contrainte unique :** `(user_id, program_id, academic_year)` → `uq_user_program_academic_year`.
- **Relations :** 1→1 vers `interviews`, 1→1 vers `interview_results`, 1→N vers `documents`.

#### Table `interviews`
Rendez-vous et convocations aux entretiens d'évaluation et de sélection.
- **Colonnes :** `id` (UUID PK), `application_id` (FK → `applications.id` CASCADE UNIQUE), `scheduled_at` (TIMESTAMPTZ), `duration_minutes` (INT), `interview_type` (ENUM `en_ligne`, `presentiel`), `location_or_link` (VARCHAR(300)), `status` (ENUM `programme`, `confirme`, `effectue`, `annule`), `interviewer_id` (FK → `users.id` SET NULL), `notes` (TEXT), `created_at` (TIMESTAMPTZ).

#### Table `interview_results`
Résultats, grille de notation et avis du jury après entretien.
- **Colonnes :** `id` (UUID PK), `interview_id` (FK → `interviews.id` CASCADE UNIQUE), `application_id` (FK → `applications.id` CASCADE UNIQUE), `technical_score` (NUMERIC(4,2)), `motivation_score` (NUMERIC(4,2)), `language_score` (NUMERIC(4,2)), `overall_score` (NUMERIC(4,2)), `decision` (ENUM `favorable`, `defavorable`, `liste_attente`), `jury_feedback` (TEXT), `evaluated_at` (TIMESTAMPTZ).

---

### SA-14 — Documents, versions et synchronisation vectorielle

#### Table `documents`
Pièces jointes associées aux dossiers de candidature.
- **Colonnes :** `id` (UUID PK), `application_id` (FK → `applications.id` CASCADE), `user_id` (FK → `users.id` CASCADE), `document_type` (ENUM `diplome`, `releve_notes`, `cin`, `cv`, `autre`), `filename` (VARCHAR(255)), `file_path` (VARCHAR(500)), `mime_type` (VARCHAR(100)), `file_size` (INT), `current_version` (INT DEFAULT 1), `is_verified` (BOOLEAN), `created_at` (TIMESTAMPTZ).
- **Relations :** 1→N vers `document_versions`.

#### Table `document_versions`
Historique des versions révisées d'un document importé.
- **Colonnes :** `id` (UUID PK), `document_id` (FK → `documents.id` CASCADE), `version_number` (INT), `file_path` (VARCHAR(500)), `file_size` (INT), `change_summary` (VARCHAR(255)), `created_at` (TIMESTAMPTZ).

#### Table `vector_sync_tasks`
Suivi des traitements automatiques de mise à jour de la base vectorielle (RAG / embeddings).
- **Colonnes :** `id` (UUID PK), `document_id` (FK → `documents.id` CASCADE NULLABLE), `action` (ENUM `upsert`, `delete`), `status` (ENUM `pending`, `processing`, `completed`, `failed`), `embedding_model` (VARCHAR(100)), `collection_name` (VARCHAR(100)), `chunk_count` (INT), `vector_dimensions` (INT DEFAULT 1536), `error_message` (TEXT), `created_at` / `processed_at` (TIMESTAMPTZ).

#### Table `sync_logs`
Journal de synchronisation global des référentiels et du catalogue.
- **Colonnes :** `id` (UUID PK), `entity_type` (VARCHAR(50)), `status` (ENUM `in_progress`, `success`, `failed`), `records_synced` (INT), `error_message` (TEXT), `started_at` / `completed_at` (TIMESTAMPTZ).

---

### SA-26 — Mémoire temporaire des conversations

#### Table `visitor_sessions`
Sessions anonymes visiteurs (hachage SHA-256 du jeton opaque, rétention et expiration).
- **Colonnes :** `id` (UUID PK), `token_hash` (VARCHAR(64) UNIQUE), `created_at`, `last_seen_at`, `expires_at` (TIMESTAMPTZ), `user_id` (FK → `users.id` SET NULL).

#### Table `conversations`
Sessions de dialogue avec l'agent IA.
- **Colonnes :** `id` (UUID PK), `session_id` (FK → `visitor_sessions.id` CASCADE), `user_id` (FK → `users.id` SET NULL), `title` (VARCHAR(200)), `created_at` (TIMESTAMPTZ).

#### Table `messages`
Messages échangés constituant la mémoire conversationnelle du LLM.
- **Colonnes :** `id` (UUID PK), `conversation_id` (FK → `conversations.id` CASCADE), `role` (ENUM `user`, `assistant`, `system`), `content` (TEXT), `created_at` (TIMESTAMPTZ).
- **Mécanisme :** Chargement contextuel des $N$ derniers messages (`get_conversation_memory`) et purge automatique en cascade lors de l'expiration des sessions.

---

## 3. Schéma relationnel complet

```
users ────────────────────────────────┬───────────────────────────┬───────────────────────┐
  │ 1→1                               │ 1→N                       │ 1→N                   │ 1→N
  ▼                                   ▼                           ▼                       ▼
academic_profiles                applications ─────────────── documents ──────────── equivalences
                                   │ 1→1         │ 1→1            │ 1→N
                                   ▼             ▼                ▼
                              interviews  interview_results  document_versions
                                   │
                                   │ (résultat lié)
                                   ▼
                              interview_results

programs ────────────────────────┬───────────────────────┬───────────────────────┐
  │ 1→N                          │ 1→N                   │ 1→N                   │ 1→N
  ▼                              ▼                       ▼                       ▼
specialties ──── 1→N ─────── courses           admission_conditions           tariffs

visitor_sessions ─── 1→N ─── conversations ─── 1→N ─── messages (SA-26)

vector_sync_tasks (suivi RAG vectoriel)
sync_logs         (audit global de synchronisation)
```

---

## 4. Migrations Alembic (SA-17)

1. `001_initial_schema` :
   - Tables : `users`, `programs`, `admission_conditions`, `tariffs`, `visitor_sessions`, `conversations`.
2. `002_candidatures_docs_msgs` :
   - Tables : `messages`, `applications`, `documents`, `sync_logs`.
3. `003_academic_interviews_versions` :
   - Tables : `specialties`, `courses`, `academic_profiles`, `equivalences`, `interviews`, `interview_results`, `document_versions`, `vector_sync_tasks`.
4. `004_add_academic_roles` :
   - Type ENUM `role` : extension native PostgreSQL avec `ALTER TYPE role ADD VALUE IF NOT EXISTS` pour les 4 rôles (`responsable_academique_iit`, `responsable_academique_isb`, `responsable_entretien`, `direction`).
   - Endpoint tableau de bord et KPI : `GET /dashboard/stats`.
   - Contrôle d'accès granulaire RBAC pour les formations IIT/ISB, les entretiens et les équivalences.

---

## 5. Données officielles & Corpus RAG — `db/seed.py` (SA-14, SA-18)

Le catalogue académique et le socle documentaire ont été intégralement mis à jour avec les **données réelles extraites des sites officiels** de l'**IIT** (https://iit.tn/) et de l'**ISB** (https://isb.tn/) (Corpus RAG officiel du 19/11/2026) :

- **32 formations officielles complètes (IIT & ISB)** :
  - **IIT (10 formations)** : Cycle préparatoire (MP1, MP2), Licence SEIER, Licence Mécatronique, Licence Informatique (4 parcours : Réseaux & Cyber, Embarqués & IoT, Big Data, Génie Logiciel), Cycle Ingénieur accrédité EUR-ACE (Génie Informatique avec options GLID, ARSI, SDIA ; Génie des Procédés ; Génie Industriel ; Génie Mécanique ; Génie Civil), Diplôme National d'Architecte (5 ans).
  - **ISB (22 formations)** : 12 Licences (Business Administration en anglais, Business Intelligence, Management, Comptabilité, Finance, Logistique, Marketing, RH, Business Economics en anglais, Transport, Droit des Affaires, Droit Privé) et 10 Mastères / MBA (MBA en anglais, MSc Finance, MSc Digital Marketing, Mastères pro...).
- **45 spécialités officielles** et **74 matières/syllabus semestriels** avec coefficients et crédits ECTS.
- **33 conditions d'admission officielles** intégrant la procédure de concours, test d'admission, commission d'au moins 3 enseignants et prérequis diplômes.
- **32 grilles tarifaires réelles** :
  - Formule IIT en 9 mensualités + 800 DT de droit d'inscription, remise de 5% pour paiement comptant, majoration de 5% à partir de la 2e année.
  - Fourchettes officielles ISB (Licences 4000-6000 DT/an, Mastères/MBA 5000-8000 DT/an) + droit d'inscription 300-500 DT.
  - Avertissement RAG obligatoire sur le statut indicatif des frais (`non_verifie, à confirmer auprès de l'administration`).
- **41 documents RAG officiels** indexés dans la table `documents` et synchronisés dans `vector_sync_tasks` avec statut `completed` et métadonnées complètes (`document_id`, `source_url`, `statut_verification`, `etablissement`).
- **Compte candidat démo** (`candidat.demo@smartcampus.tn`) avec profil académique complet, candidature démo, versioning documentaire, entretien d'évaluation favorable et demande d'équivalence validée.
- **Audit de synchronisation** tracé automatiquement dans `sync_logs`.

---

## 6. Fiabilité et Tests des API (SA-22)

La suite de tests automatisés (`pytest` — **42 tests réussis à 100%**) vérifie l'ensemble des règles métier :
1. `tests/test_academic_advanced.py` :
   - Spécialités & cours (création réservée à l'admin, filtres par semestre et spécialité).
   - Profils académiques (upsert, contrôle d'accès candidat).
   - Équivalences (dépôt candidat, revue et validation par le jury/admin).
   - Entretiens & résultats (programmation, détection des doublons 409, calcul de moyenne, avis favorable/défavorable).
   - Versioning documentaire & synchronisation vectorielle (tâches RAG).
2. `tests/test_candidatures_documents.py` : cycle des candidatures, documents et contrôle RBAC.
3. `tests/test_flow.py` : cycle visiteur → conversation → inscription → liaison.
4. `tests/test_llm_dialogue.py` : mémoire conversationnelle, moteur RAG et dialecte tunisien / Arabizi.
5. `tests/test_security.py` & `test_remediation.py` : validation des types, formats d'années académiques `AAAA-AAAA`, précision monétaire `Numeric(10,2)`, et rate-limiting.
6. `tests/test_concurrency.py` : verrous pessimistes PostgreSQL (`SELECT ... FOR UPDATE` avec `populate_existing=True`).

---

## 7. Conformité aux Règles du Corpus RAG

| Règle | Implémentation | Statut |
|---|---|:---:|
| **1. Unité documentaire atomique** | Chaque document du corpus conserve son intégrité dans `data/corpus_rag_iit_isb.json` et en base. | ✅ Conforme |
| **2. Métadonnées préservées** | `document_id`, `etablissement`, `source_url`, `type`, `statut_verification` attachés à chaque fiche. | ✅ Conforme |
| **3. Statut `non_verifie` respecté** | Avertissement systématique : les montants et conditions sont présentés comme indicatifs et à revalider. | ✅ Conforme |
| **4. Données absentes / partielles** | Indication claire de l'absence de l'information et réorientation vers les contacts officiels (emails). | ✅ Conforme |
| **5. Tarifs et échéances avec prudence** | Mention des formules (9 mensualités + 800 DT inscription pour l'IIT, fourchettes pour l'ISB). | ✅ Conforme |
| **6. Citation obligatoire des sources** | Chaque réponse générée cite formellement `document_id` et son URL source officielle `source_url`. | ✅ Conforme |
| **7. Pas de déduction arbitraire** | Rappel explicite que l'admissibilité et les équivalences relèvent de la commission d'admission. | ✅ Conforme |

