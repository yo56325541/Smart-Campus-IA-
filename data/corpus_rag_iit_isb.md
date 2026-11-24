# CORPUS RAG — IIT & ISB (Sfax)

> **Projet :** SmartCampus AI — Orientation universitaire  
> **Sources officielles :** [https://iit.tn/](https://iit.tn/) · [https://isb.tn/](https://isb.tn/)  
> **Date de collecte déclarée :** 2026-11-19  
> **Version de préparation :** 1.0  

---

## Règles d'utilisation pour le RAG
1. Chaque bloc `DOCUMENT` constitue une unité documentaire source.
2. Conserver `document_id`, `etablissement`, `source_url`, `type` et `statut_verification` dans les métadonnées de chaque chunk.
3. Ne jamais présenter une information marquée `non_verifie`, `à confirmer`, `partielle` ou `manquante` comme une information officielle confirmée.
4. En cas d'information absente, répondre qu'elle n'est pas précisée dans le corpus et orienter vers le contact officiel si disponible.
5. Les frais, dates limites, campagnes d'admission et coordonnées doivent être revalidés avant toute réponse engageante.
6. Les réponses générées doivent citer le nom du document et son `source_url`.
7. Ne pas déduire une équivalence de diplôme, une admissibilité ou une décision d'admission à partir d'une simple proximité de spécialité.

---

## Documents IIT (Institut International de Technologie)

### DOCUMENT : frais-et-conditions-generales-iit
- **document_id** : `frais-et-conditions-generales-iit`
- **source_url** : https://iit.tn/test/procedure-et-frais-dinscription/
- **statut_verification** : `non_verifie (frais indicatifs, à confirmer par l'administration)`
- **Frais de scolarité (indicatifs 1ère année)** :
  - Cycle préparatoire : 556 DT / 9 mois (national), 234 € / 9 mois (international).
  - Licences SEIER et Mécatronique : 567 DT / 9 mois (national), 167 € / 9 mois (international).
  - Licences informatique (Réseaux & Cybersécurité, Embarqués & IoT, Big Data, Génie Logiciel) : 667 DT / 9 mois (national), 189 € / 9 mois (international).
  - Ingénierie Génie Informatique : 778 DT / 9 mois (national), 234 € / 9 mois (international).
  - Ingénierie Génie des Procédés et Génie Industriel : 611 DT / 9 mois (national), 234 € / 9 mois (international).
  - Architecture : 776 DT / 9 mois (national), 278 € / 9 mois (international).
- **Conditions générales** :
  - Droit d'inscription : 800 DT (tunisiens) ou 800 € (internationaux), en supplément des frais de scolarité.
  - Majoration annuelle de 5 % à partir de la 2e année.
  - Réduction de 5 % en cas de paiement total à l'inscription.
  - Inscription ferme et définitive, sans remboursement.

### DOCUMENT : procedure-admission-ingenierie-iit
- **document_id** : `procedure-admission-ingenierie-iit`
- **source_url** : https://iit.tn/test/procedure-et-frais-dinscription/
- **Contenu** : Admission par concours sur dossier, entretien de validation et test d'admission devant au moins trois enseignants. Résultats : accepté, refusé ou liste d'attente.

### DOCUMENT : bourses-iit
- **document_id** : `bourses-iit`
- **source_url** : https://iit.tn/test/bourse/
- **Contenu** : 4 types de bourses (Excellence, Performance, Notoriété, Aide sociale et besoins spéciaux). Plafond : 10 % des nouveaux inscrits. Demande sous 1 semaine après inscription.

### DOCUMENT : cycle-preparatoire-iit
- **document_id** : `cycle-preparatoire-iit`
- **formation** : Cycle préparatoire aux grandes écoles d'ingénieurs (MP1, MP2)
- **source_url** : https://iit.tn/prepa/
- **contact** : ameni.trigui@iit.ens.tn
- **Prérequis** : Bac scientifique (Math, Sciences, Info, Technique).
- **Matières** : Physique, Analyse, Algèbre, Chimie, Informatique, S.T.A, Anglais, Français.
- **Frais** : 556 DT / 9 mois (+ 800 DT inscription).

### DOCUMENT : licence-seier-iit
- **document_id** : `licence-seier-iit`
- **formation** : Systèmes Électriques Intelligents & Énergies Renouvelables (SEIER)
- **source_url** : https://iit.tn/licence-en-systemes-electriques-intelligents-energies-renouvelables/
- **contact** : amira.bouaziz@iit.ens.tn
- **Frais** : 567 DT / 9 mois (+ 800 DT inscription).
- **Modules** : Sciences fondamentales, Réseaux électriques & Smart Grids, Énergies renouvelables (solaire, éolien), Automatisation (API, SCADA, IoT, IA).

### DOCUMENT : licence-mecatronique-iit
- **document_id** : `licence-mecatronique-iit`
- **formation** : Mécatronique & Systèmes Intelligents
- **source_url** : https://iit.tn/licence-en-mecatronique-systemes-intelligents/
- **contact** : amira.bouaziz@iit.ens.tn
- **Frais** : 567 DT / 9 mois (+ 800 DT inscription).
- **Modules** : Informatique & IA (Python, vision industrielle), Robotique mobile et drones, Automatisation & embarqué, Industrie 4.0.

### DOCUMENT : licence-informatique-presentation-generale-iit
- **document_id** : `licence-informatique-presentation-generale-iit`
- **formation** : Licence en Informatique (4 parcours)
- **source_url** : https://iit.tn/licences/
- **contact** : Omar.Khrouf@iit.ens.tn
- **Frais** : 667 DT / 9 mois (+ 800 DT inscription).
- **Parcours** : Réseaux & Cybersécurité, Systèmes Embarqués & IoT, Big Data & Analyse de données, Génie Logiciel & Systèmes Intelligents.

### DOCUMENT : ingenierie-genie-informatique-iit
- **document_id** : `ingenierie-genie-informatique-iit`
- **formation** : Cycle Ingénieur en Génie Informatique (Accréditation ASIIN Euro-Inf Master)
- **source_url** : https://iit.tn/filieres-ingenieur/genie-informatique-2/
- **contact** : dep.tic@iit.ens.tn
- **Frais** : 778 DT / 9 mois (+ 800 DT inscription).
- **3 parcours** : GLID (Génie Logiciel & Décisionnel), ARSI (Réseaux & Sécurité), SDIA (Data Science & IA).

### DOCUMENT : ingenierie-genie-procedes-iit
- **document_id** : `ingenierie-genie-procedes-iit`
- **formation** : Génie des Procédés
- **source_url** : https://iit.tn/genie-des-procedes/
- **contact** : dep.procedes@iit.ens.tn
- **Frais** : 611 DT / 9 mois (+ 800 DT inscription).

### DOCUMENT : ingenierie-genie-industriel-iit
- **document_id** : `ingenierie-genie-industriel-iit`
- **formation** : Génie Industriel
- **source_url** : https://iit.tn/filieres-ingenieur/genie-industriel-2/
- **contact** : Dep.industriel@iit.ens.tn
- **Frais** : 611 DT / 9 mois (+ 800 DT inscription).

### DOCUMENT : ingenierie-genie-mecanique-iit
- **document_id** : `ingenierie-genie-mecanique-iit`
- **source_url** : https://iit.tn/filieres-ingenieur/genie-mecanique-2/

### DOCUMENT : ingenierie-genie-civil-iit
- **document_id** : `ingenierie-genie-civil-iit`
- **source_url** : https://iit.tn/filieres-ingenieur/genie-civil/

### DOCUMENT : architecture-iit
- **document_id** : `architecture-iit`
- **formation** : Architecture (ISA, 6 ans)
- **source_url** : https://iit.tn/architecture-2/
- **contact** : hager.bejaoui@iit.ens.tn
- **Frais** : 776 DT / 9 mois (+ 800 DT inscription).

---

## Documents ISB (International School of Business)

### DOCUMENT : admission-et-preinscription-isb
- **document_id** : `admission-et-preinscription-isb`
- **source_url** : https://isb.tn/pre-inscription/
- **contact** : info@isb.ens.tn · +216 74 248 222

### Formations Licences ISB (180 crédits, 3 ans) :
- `licence-business-administration-isb` (100% anglais, https://isb.tn/program-lba/)
- `licence-business-intelligence-isb` (bilingue FR/EN, Certifs NVIDIA & Power BI, https://isb.tn/business-intelligence/)
- `licence-management-isb` (https://isb.tn/management/)
- `licence-comptabilite-isb` (https://isb.tn/comptabilite/)
- `licence-finance-isb` (https://isb.tn/finance/)
- `licence-logistique-production-isb` (https://isb.tn/logistique-et-production/)
- `licence-marketing-isb` (https://isb.tn/marketing/)
- `licence-ressources-humaines-isb` (https://isb.tn/ressources-humaines/)
- `licence-business-economics-isb` (https://isb.tn/business-economics-2/)
- `licence-transport-logistique-isb` (https://isb.tn/licence-nationale-en-ingenierie-economique-et-financiere/)
- `licence-droit-des-affaires-isb` (https://isb.tn/droit-des-affaires-2/)
- `licence-droit-prive-isb` (https://isb.tn/droit-prive-2/)

### Formations Masters & MBA ISB (120 crédits, 2 ans) :
- `master-mba-isb` (1er MBA de Sfax, anglais, https://isb.tn/program-mba/)
- `master-science-finance-isb` (MSc Finance, option Finance Digitale, https://isb.tn/program-msf/)
- `master-marketing-digital-anglais-isb` (anglais, https://isb.tn/mmd-en/)
- `mastere-marketing-digital-fr-isb` (français CréaDataIA, https://isb.tn/mmd/)
- `mastere-comptabilite-isb` (préparation CES révision comptable, https://isb.tn/program-mpc/)
- `mastere-finance-entreprise-isb` (option Finance Digitale, https://isb.tn/program-minf/)
- `mastere-droit-affaires-co-construit-isb` (ISL, https://isb.tn/master-in-business-law-english/)
- `mastere-marketing-distribution-relation-client-isb` (https://isb.tn/marketing-distribution-et-relation-client/)
- `mastere-management-marketing-agroalimentaire-isb` (https://isb.tn/management-et-marketing-des-produits-agroalimentaires/)
- `mastere-audit-interne-isb` (préparation CIA / CISA, https://isb.tn/audit-interne/)
