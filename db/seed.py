"""Script d'alimentation de la base de données avec des données réelles officielles (SA-18).
Catalogue académique complet pour l'Institut International de Technologie (IIT, https://iit.tn/)
et l'International School of Business (ISB, https://isb.tn/).
Source : Corpus officiel extrait le 2026-11-19.
Couvre : Formations, Spécialités, Matières (Courses), Conditions, Tarifs, Candidats de démo,
Profils académiques, Équivalences, Entretiens, Résultats, Documents RAG et Tâches vectorielles (SA-14, SA-18).
"""
import json
import logging
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import (
    AcademicProfile,
    AdmissionCondition,
    Application,
    ApplicationStatus,
    Course,
    Document,
    DocumentType,
    DocumentVersion,
    EquivalenceRequest,
    EquivalenceStatus,
    Institution,
    InterviewAppointment,
    InterviewResult,
    InterviewStatus,
    JuryDecision,
    Program,
    Role,
    Specialty,
    SyncLog,
    SyncStatus,
    Tariff,
    User,
    VectorSyncAction,
    VectorSyncStatus,
    VectorSyncTask,
)
from app.security import hash_password

logger = logging.getLogger("smartcampus.seed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEMO_PROGRAMS = [
    # ========================== IIT (Institut International de Technologie) ==========================
    {
        "slug": "iit-cycle-preparatoire",
        "institution": Institution.IIT,
        "level": "prepa",
        "name": "Cycle préparatoire aux grandes écoles d'ingénieurs",
        "description": "Cycle préparatoire scientifique (MP1 et MP2) accessible à partir d'un baccalauréat scientifique. Formation solide en mathématiques, physique, chimie et informatique avec encadrement rigoureux.",
        "duration_years": 2,
        "language": "fr",
        "careers": "Poursuite en cycle ingénieur : Génie Informatique, Génie Civil, Génie Industriel, Génie des Procédés, Génie Mécanique.",
        "specialties": [
            {"code": "PREPA-MP1", "name": "MP1 - Première Année Math-Physique", "description": "Bases approfondies en analyse, algèbre et physique."},
            {"code": "PREPA-MP2", "name": "MP2 - Deuxième Année Math-Physique", "description": "Préparation aux concours et admission en cycle ingénieur."},
        ],
        "courses": [
            {"code": "PREPA-101", "name": "Analyse & Algèbre Linéaire", "semester": "S1", "credits_ects": Decimal("6.0"), "coefficient": Decimal("3.00"), "hours_lectures": 42, "hours_tutorials": 42, "description": "Espaces vectoriels, séries, intégration, calcul différentiel."},
            {"code": "PREPA-102", "name": "Physique Générale & Électromagnétisme", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.50"), "hours_lectures": 35, "hours_tutorials": 35, "description": "Optique géométrique, thermodynamique, électrostatique."},
            {"code": "PREPA-201", "name": "Chimie des Solutions & Organique", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Cinétique chimique, équilibres acido-basiques, oxydoréduction."},
            {"code": "PREPA-202", "name": "Algorithmique & Programmation Python/C", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Structures de données, algorithmique fondamentale."},
        ],
        "conditions": [
            {"title": "Baccalauréat Scientifique", "description": "Baccalauréat en Mathématiques, Sciences Expérimentales, Informatique ou Technique.", "required_diploma": "Baccalauréat Scientifique", "min_average": Decimal("10.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("5004.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "556 DT/mois sur 9 mois + 800 DT inscription (234 €/mois + 800 € international). -5% si paiement au comptant. Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-licence-seier",
        "institution": Institution.IIT,
        "level": "licence",
        "name": "Licence en Systèmes Électriques Intelligents & Énergies Renouvelables (SEIER)",
        "description": "Formation préparant les acteurs de la transition énergétique : systèmes électriques intelligents, Smart Grids, énergies renouvelables (solaire, éolien), IoT, automatisation et IA appliquée à l'énergie.",
        "duration_years": 3,
        "language": "fr/en",
        "careers": "Ingénieur systèmes électriques intelligents, ingénieur énergies renouvelables, ingénieur Smart Grids, responsable efficacité énergétique, consultant transition énergétique.",
        "specialties": [
            {"code": "SEIER-SG", "name": "Smart Grids & Réseaux Électriques Intelligents", "description": "Conception, distribution et intégration des énergies renouvelables."},
            {"code": "SEIER-AUTO", "name": "Automatisation & Numérique Énergétique", "description": "Automatique, API/PLC, SCADA, IoT et IA appliquée à l'énergie."},
        ],
        "courses": [
            {"code": "SEI-101", "name": "Électrotechnique & Électronique de Puissance", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Convertisseurs statiques, onduleurs, machines électriques."},
            {"code": "SEI-102", "name": "Énergies Renouvelables (Solaire & Éolien)", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Photovoltaïque, stockage d'énergie et gestion énergétique."},
            {"code": "SEI-201", "name": "Smart Grids & Supervision SCADA", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Réseaux communicants, supervision industrielle, efficacité énergétique."},
            {"code": "SEI-202", "name": "Automatique, API & IoT Industriel", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Automates programmables, capteurs connectés et Edge Computing."},
        ],
        "conditions": [
            {"title": "Baccalauréat Scientifique ou Technique", "description": "Baccalauréat en Mathématiques, Sciences Expérimentales, Informatique ou Technique.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("5103.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "567 DT/mois sur 9 mois + 800 DT inscription (167 €/mois + 800 € international). Majoration de 5% à partir de la 2e année. Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-licence-mecatronique",
        "institution": Institution.IIT,
        "level": "licence",
        "name": "Licence en Mécatronique & Systèmes Intelligents",
        "description": "Parcours combinant robotique, intelligence artificielle, systèmes embarqués et automatisation industrielle au cœur de l'Industrie 4.0. Enseignée en français et en anglais.",
        "duration_years": 3,
        "language": "fr/en",
        "careers": "Concepteur mécatronique, intégrateur robotique/automatismes, roboticien, technicien Industrie 4.0, chef de projet IoT.",
        "specialties": [
            {"code": "MEC-ROB", "name": "Robotique & Systèmes Mobiles", "description": "Robotique mobile, drones, cinématique et dynamique des robots."},
            {"code": "MEC-IND4", "name": "Industrie 4.0 & Systèmes Embarqués", "description": "Microcontrôleurs, Edge Computing, vision industrielle et maintenance prédictive."},
        ],
        "courses": [
            {"code": "MEC-101", "name": "Mécanique du Solide & Conception CAO", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Statique, cinématique, modélisation SolidWorks."},
            {"code": "MEC-102", "name": "Microcontrôleurs & Systèmes Temps Réel", "semester": "S1", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Architecture ARM, périphériques embarqués, langage C/C++ embarqué."},
            {"code": "MEC-201", "name": "Robotique & Vision Industrielle IA", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Traitement d'images, OpenCV, apprentissage profond pour vision robotique."},
            {"code": "MEC-202", "name": "Automatique & Actionneurs Électriques", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Asservissements, moteurs pas à pas, brushless, régulation PID."},
        ],
        "conditions": [
            {"title": "Baccalauréat Scientifique ou Technique", "description": "Baccalauréat en Mathématiques, Sciences Expérimentales, Informatique ou Technique.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("5103.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "567 DT/mois sur 9 mois + 800 DT inscription (167 €/mois + 800 € international). Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-licence-informatique",
        "institution": Institution.IIT,
        "level": "licence",
        "name": "Licence en Sciences Informatiques (4 Parcours)",
        "description": "Formation de référence proposant 4 parcours spécialisés dès la 1ère année : (1) Réseaux & Cybersécurité, (2) Systèmes Embarqués & IoT, (3) Big Data & Analyse de Données, (4) Génie Logiciel & Systèmes d'Information.",
        "duration_years": 3,
        "language": "fr/en",
        "careers": "Développeur Full Stack, Data Analyst, Administrateur Cybersécurité, Ingénieur IoT junior, Consultant ERP.",
        "specialties": [
            {"code": "INFO-SEC", "name": "Réseaux & Cybersécurité", "description": "Sécurité des infrastructures, détection d'intrusions, cryptographie et administration réseaux."},
            {"code": "INFO-IOT", "name": "Systèmes Embarqués & IoT", "description": "Capteurs intelligents, microcontrôleurs, Edge AI et protocoles connectés (MQTT, LoRa)."},
            {"code": "INFO-DATA", "name": "Big Data & Analyse de Données", "description": "Pipelines ETL, entrepôts de données, machine learning et visualisation Power BI / Tableau."},
            {"code": "INFO-GL", "name": "Génie Logiciel & Systèmes d'Information", "description": "Architectures logicielles modernes, frameworks web/cloud, bases de données et DevOps."},
        ],
        "courses": [
            {"code": "INF-101", "name": "Algorithmique Avancée & Structures de Données", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Listes, arbres, graphes, tables de hachage, complexité algorithmique."},
            {"code": "INF-102", "name": "Bases de Données Relationnelles & SQL", "semester": "S1", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Modélisation relationnelle, algèbre relationnelle, requêtes SQL avancées."},
            {"code": "INF-201", "name": "Réseaux Informatiques & Sécurité de Base", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Modèle OSI, TCP/IP, routage, filtrage firewall et protocoles de chiffrement."},
            {"code": "INF-202", "name": "Développement Web Full-Stack & APIs REST", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Architectures client-serveur, React, Node.js, FastAPI, conteneurisation Docker."},
        ],
        "conditions": [
            {"title": "Baccalauréat Scientifique ou Économie (Data)", "description": "Baccalauréat en Mathématiques, Sciences Expérimentales, Informatique, Technique ou Économie-Gestion.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("6003.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "667 DT/mois sur 9 mois + 800 DT inscription (189 €/mois + 800 € international). -5% si paiement comptant. Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-cycle-ingenieur-informatique",
        "institution": Institution.IIT,
        "level": "ingenierie",
        "name": "Cycle Ingénieur en Génie Informatique (EUR-ACE)",
        "description": "Diplôme national d'ingénieur accrédité par le label européen EUR-ACE. Propose 3 options professionnelles : GLID (Génie Logiciel et Informatique Décisionnelle), ARSI (Administration des Réseaux et Sécurité Informatique), et SDIA (Systèmes Distribués et Intelligence Artificielle).",
        "duration_years": 3,
        "language": "fr/en",
        "careers": "Ingénieur Logiciel, Architecte Cloud & DevOps, Ingénieur IA / Machine Learning, Expert Cybersécurité, Data Engineer.",
        "specialties": [
            {"code": "ING-GLID", "name": "Génie Logiciel & Informatique Décisionnelle (GLID)", "description": "Ingénierie des exigences, design patterns, microservices, architectures décisionnelles."},
            {"code": "ING-ARSI", "name": "Administration des Réseaux & Sécurité Informatique (ARSI)", "description": "Sécurité offensive et défensive, cryptographie, infrastructures cloud et réseaux SD-WAN."},
            {"code": "ING-SDIA", "name": "Systèmes Distribués & Intelligence Artificielle (SDIA)", "description": "Apprentissage profond, traitement du langage naturel, calcul distribué et MLOps."},
        ],
        "courses": [
            {"code": "ING-INF-401", "name": "Architectures Distribuées & Microservices", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Architectures événementielles, Kafka, Docker, Kubernetes, gRPC."},
            {"code": "ING-INF-402", "name": "Intelligence Artificielle & Deep Learning", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Réseaux de neurones, CNN, transformers, PyTorch, vision par ordinateur."},
            {"code": "ING-INF-501", "name": "Cybersécurité Avancée & Tests d'Intrusion", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Pentesting, analyse de vulnérabilités, OWASP Top 10, conformité ISO 27001."},
            {"code": "ING-INF-502", "name": "Cloud Computing & Pratiques DevOps", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "CI/CD GitLab, Terraform, monitoring Prometheus/Grafana, cloud public AWS/Azure."},
        ],
        "conditions": [
            {"title": "Admission sur Concours / Dossier", "description": "Concours sur dossier, entretien de validation pédagogique et test d'admission devant une commission d'au moins 3 enseignants.", "required_diploma": "Prépa ou Licence", "min_average": Decimal("11.00"), "position": 1},
            {"title": "Diplômes admis", "description": "Diplôme de cycle préparatoire (MP/PC/PT) ou Licence en Informatique, Mathématiques ou équivalent scientifique.", "required_diploma": "Bac+2 ou Bac+3", "min_average": None, "position": 2},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("7002.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "778 DT/mois sur 9 mois + 800 DT inscription (234 €/mois + 800 € international). -5% si paiement comptant. Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-cycle-ingenieur-genie-procedes",
        "institution": Institution.IIT,
        "level": "ingenierie",
        "name": "Cycle Ingénieur en Génie des Procédés",
        "description": "Formation d'ingénieur dédiée à la transformation industrielle de la matière et de l'énergie : génie chimique, biotechnologies, procédés environnementaux, traitement des eaux et agroalimentaire.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Ingénieur Procédés, Responsable Sécurité des Procédés Industriels, Ingénieur Traitement de l'Eau, Consultant Environnement.",
        "specialties": [
            {"code": "GP-IND", "name": "Procédés Industriels & Environnement", "description": "Opérations unitaires, traitement des rejets, bilan matière et énergie."},
            {"code": "GP-PHARM", "name": "Génie Chimique & Pharmaceutique", "description": "Synthèse industrielle, bioprocédés, validation BPF et formulation."},
        ],
        "courses": [
            {"code": "GP-401", "name": "Thermodynamique des Procédés & Transferts", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Transfert de chaleur, transfert de matière, équilibres de phases."},
            {"code": "GP-402", "name": "Réacteurs Chimiques & Opérations Unitaires", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Distillation, absorption, extraction liquide-liquide, dimensionnement."},
        ],
        "conditions": [
            {"title": "Cycle préparatoire ou Licence Scientifique", "description": "Prépa PC/MP ou Licence en Chimie, Biologie, Énergie, Procédés.", "required_diploma": "Prépa ou Licence", "min_average": Decimal("11.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("5499.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "611 DT/mois sur 9 mois + 800 DT inscription (234 €/mois + 800 € international). Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-cycle-ingenieur-genie-industriel",
        "institution": Institution.IIT,
        "level": "ingenierie",
        "name": "Cycle Ingénieur en Génie Industriel",
        "description": "Optimisation de la performance globale des entreprises industrielles et de services : supply chain management, lean manufacturing, amélioration continue, ERP et transition Industrie 4.0.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Ingénieur Supply Chain, Responsable Lean Manufacturing, Responsable Méthodes & Qualité, Chef de Projet Industrie 4.0.",
        "specialties": [
            {"code": "GI-SUPPLY", "name": "Supply Chain & Logistique Globale", "description": "Planification avancée, gestion des flux, approvisionnements et distribution."},
            {"code": "GI-LEAN", "name": "Lean Manufacturing & Qualité", "description": "Six Sigma, TPM, SMED, amélioration continue et certification qualité."},
        ],
        "courses": [
            {"code": "GI-401", "name": "Gestion de Production & Progiciels ERP", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "MRP2, ordonnancement, gestion des stocks, intégration ERP SAP/Odoo."},
            {"code": "GI-402", "name": "Recherche Opérationnelle & Simulation de Flux", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Programmation linéaire, graphes, théorie des files d'attente, simulation Arena."},
        ],
        "conditions": [
            {"title": "Cycle préparatoire ou Licence Technique", "description": "Prépa MP/PC/PT ou Licence en Génie Industriel, Mécanique, Gestion de Production.", "required_diploma": "Prépa ou Licence", "min_average": Decimal("11.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("5499.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "611 DT/mois sur 9 mois + 800 DT inscription (234 €/mois + 800 € international). Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-cycle-ingenieur-genie-mecanique",
        "institution": Institution.IIT,
        "level": "ingenierie",
        "name": "Cycle Ingénieur en Génie Mécanique",
        "description": "Ingénierie de conception et de fabrication mécanique : modélisation 3D avancée, simulation numérique par éléments finis, fabrication additive, matériaux composites et maintenance mécatronique.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Ingénieur R&D Mécanique, Ingénieur Calcul de Structures, Responsable Bureau d'Études, Ingénieur Mécatronique Industrielle.",
        "specialties": [
            {"code": "GM-CAD", "name": "Conception & Simulation Numérique (CAO/FEA)", "description": "Éléments finis, calcul non-linéaire, optimisation topologique et CAO Catia/SolidWorks."},
            {"code": "GM-FAB", "name": "Fabrication Avancée & Matériaux", "description": "Usinage CNC 5 axes, fabrication additive métallique, métallurgie et matériaux composites."},
        ],
        "courses": [
            {"code": "GM-401", "name": "Mécanique des Milieux Continus & Éléments Finis", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Tenseurs, élasticité, plasticité, formulation par éléments finis sous ANSYS."},
            {"code": "GM-402", "name": "Conception Mécanique Avancée & Prototypage", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Dimensionnement d'organes de machines, fatigue des matériaux, fabrication additive."},
        ],
        "conditions": [
            {"title": "Cycle préparatoire ou Licence Mécanique", "description": "Prépa PT/MP/PC ou Licence en Génie Mécanique, Électromécanique.", "required_diploma": "Prépa ou Licence", "min_average": Decimal("11.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("5499.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "611 DT/mois sur 9 mois + 800 DT inscription (234 €/mois + 800 € international). Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-cycle-ingenieur-genie-civil",
        "institution": Institution.IIT,
        "level": "ingenierie",
        "name": "Cycle Ingénieur en Génie Civil",
        "description": "Spécialisation dans les structures durables, la modélisation BIM, la mécanique des sols, l'hydraulique et le management des grands chantiers d'infrastructure et de travaux publics.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Ingénieur Calcul de Structures, Conducteur de Travaux, Ingénieur BIM Manager, Expert Géotechnique.",
        "specialties": [
            {"code": "GC-STRUCT", "name": "Structures & Ouvrages d'Art", "description": "Béton armé, béton précontraint, charpentes métalliques et parasismique."},
            {"code": "GC-BIM", "name": "Bâtiments Durables & Modélisation BIM", "description": "Efficacité énergétique des bâtiments, maquette numérique Revit, éco-matériaux."},
        ],
        "courses": [
            {"code": "GC-401", "name": "Mécanique des Sols & Géotechnique Avancée", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Capacité portante, tassements, soutènements, fondations profondes."},
            {"code": "GC-402", "name": "Béton Armé & Eurocodes 2", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "États limites ultimes (ELU) et de service (ELS), dimensionnement de poutres, dalles et poteaux."},
        ],
        "conditions": [
            {"title": "Cycle préparatoire ou Licence Génie Civil", "description": "Prépa scientifique ou Licence en Génie Civil / BTP.", "required_diploma": "Prépa ou Licence", "min_average": Decimal("11.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("5499.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "611 DT/mois sur 9 mois + 800 DT inscription (234 €/mois + 800 € international). Frais indicatifs."},
        ],
    },
    {
        "slug": "iit-architecture",
        "institution": Institution.IIT,
        "level": "ingenierie",
        "name": "Diplôme National d'Architecte",
        "description": "Cursus complet de 5 ans formant des architectes créatifs et techniquement compétents, alliant conception architecturale, urbanisme, écoconception, patrimoine et technologies numériques.",
        "duration_years": 5,
        "language": "fr",
        "careers": "Architecte concepteur, Urbaniste, Maître d'œuvre, Consultant en écoconception, Scénographe.",
        "specialties": [
            {"code": "ARCH-URB", "name": "Architecture, Ville & Territoire", "description": "Projets d'aménagement urbain durable, requalification patrimoniale."},
            {"code": "ARCH-ECO", "name": "Écoconception & Technologies Paramétriques", "description": "Architecture bioclimatique, simulation énergétique, design computationnel."},
        ],
        "courses": [
            {"code": "ARCH-101", "name": "Atelier de Projet Architectural 1", "semester": "S1", "credits_ects": Decimal("6.0"), "coefficient": Decimal("3.00"), "hours_lectures": 42, "hours_tutorials": 42, "description": "Espace, lumière, parcours, matérialité et dessin architectural manuel et assisté."},
            {"code": "ARCH-102", "name": "Histoire de l'Architecture & Théorie", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Des origines classiques à l'époque contemporaine, typologies spatiales."},
        ],
        "conditions": [
            {"title": "Baccalauréat toutes sections & Entretien", "description": "Baccalauréat scientifique, technique, lettres ou économie. Entretien de motivation et test d'aptitude artistique.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1},
        ],
        "tariffs": [
            {"academic_year": "2026-2027", "amount": Decimal("6984.00"), "registration_fee": Decimal("800.00"), "currency": "TND", "payment_terms": "776 DT/mois sur 9 mois + 800 DT inscription (278 €/mois + 800 € international). Frais indicatifs."},
        ],
    },

    # ========================== ISB (International School of Business) ==========================
    # --- 12 Licences ISB ---
    {
        "slug": "isb-licence-business-administration",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Business Administration (Track Anglais)",
        "description": "Programme international enseigné intégralement en anglais couvrant le management global, la finance internationale, le marketing stratégique et l'entrepreneuriat.",
        "duration_years": 3,
        "language": "en",
        "careers": "International Business Developer, Assistant Brand Manager, Junior Consultant, Operations Analyst.",
        "specialties": [{"code": "BA-INT", "name": "International Business & Management", "description": "Global strategy, cross-cultural management and trade."}],
        "courses": [
            {"code": "BA-101", "name": "Principles of Management & Organization", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Foundations of business structure, leadership and ethics."},
            {"code": "BA-102", "name": "Financial Accounting & Reporting", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Financial statements, balance sheet analysis and IFRS standards."},
        ],
        "conditions": [{"title": "Baccalauréat toutes sections", "description": "Baccalauréat avec bon niveau en langue anglaise.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("5000.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement annuel ou échelonné (fourchette indicative 4000-6000 DT/an). Inscription 400 DT. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-business-intelligence",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Business Intelligence & Analyse Décisionnelle",
        "description": "Double compétence en gestion et technologies de la donnée : analyse décisionnelle, entrepôts de données, tableaux de bord interactifs (Power BI, Tableau) et statistiques appliquées aux affaires.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Analyste BI, Data Analyst Junior, Consultant en pilotage de la performance, Concepteur de tableaux de bord exécutifs.",
        "specialties": [{"code": "BI-ANALYTICS", "name": "Business Analytics & Visualisation", "description": "Modélisation dimensionnelle, reporting dynamique et indicateurs de performance."}],
        "courses": [
            {"code": "BI-101", "name": "Introduction aux Systèmes d'Information Décisionnels", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Concepts décisionnels, ETL, schémas en étoile."},
            {"code": "BI-102", "name": "SQL & Gestion des Données d'Entreprise", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Requêtage analytique, agrégations et intégration des données."},
        ],
        "conditions": [{"title": "Baccalauréat Scientifique, Info ou Économie", "description": "Aisance avec les chiffres et la logique analytique.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("5200.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement par tranches semestrielles. Frais indicatifs (4000-6000 DT/an)."}],
    },
    {
        "slug": "isb-licence-management",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Management des Organisations",
        "description": "Maîtrise des fondamentaux du pilotage des entreprises : stratégie d'entreprise, gestion des opérations, gestion de projet, dynamique des équipes et entrepreneuriat.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Adjoint de direction, Gestionnaire de projets d'entreprise, Chargé de mission opérationnel, Créateur d'entreprise.",
        "specialties": [{"code": "MGT-STRAT", "name": "Stratégie & Gestion de Projets", "description": "Pilotage stratégique, gestion agile et transformation d'entreprise."}],
        "courses": [
            {"code": "MGT-101", "name": "Théories des Organisations & Management", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Structures organisationnelles, prise de décision et gouvernance."},
            {"code": "MGT-102", "name": "Management de Projet & Méthodes Agiles", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Planification, suivi budgétaire, Scrum et livrables de projet."},
        ],
        "conditions": [{"title": "Baccalauréat toutes sections", "description": "Baccalauréat Économie, Lettres, Sciences ou Technique.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4800.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-comptabilite",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Comptabilité & Contrôle de Gestion",
        "description": "Formation rigoureuse aux normes comptables tunisiennes et internationales (IFRS), droit fiscal, audit comptable et contrôle budgétaire.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Collaborateur en cabinet d'expertise comptable, Comptable d'entreprise, Contrôleur de gestion junior, Auditeur comptable.",
        "specialties": [{"code": "COMPT-AUDIT", "name": "Comptabilité Financière & Normes IFRS", "description": "États financiers, fiscalité des entreprises et audit légal."}],
        "courses": [
            {"code": "CPT-101", "name": "Comptabilité Générale Approfondie", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Opérations d'inventaire, amortissements, provisions et clôture."},
            {"code": "CPT-102", "name": "Fiscalité des Entreprises & TVA", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Impôt sur les sociétés, TVA, retenues à la source."},
        ],
        "conditions": [{"title": "Baccalauréat Économie, Sciences ou Maths", "description": "Baccalauréat en Économie & Gestion ou filières scientifiques.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4800.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-finance",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Finance & Banque",
        "description": "Analyse financière, gestion de portefeuille, diagnostic de santé financière des entreprises, marchés monétaires et opérations bancaires.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Chargé de clientèle professionnelle en banque, Analyste financier junior, Gestionnaire de trésorerie, Gestionnaire de portefeuille.",
        "specialties": [{"code": "FIN-BANQUE", "name": "Banque & Marchés des Capitaux", "description": "Produits de placement, crédit bancaire, évaluation des actifs financiers."}],
        "courses": [
            {"code": "FIN-101", "name": "Mathématiques Financières & Évaluation d'Actifs", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Actualisation, rentes, amortissement des emprunts, taux d'intérêt."},
            {"code": "FIN-102", "name": "Analyse Financière & Diagnostic d'Entreprise", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "SIG, CAF, BFR, ratios financiers et solvabilité."},
        ],
        "conditions": [{"title": "Baccalauréat Économie ou Scientifique", "description": "Baccalauréat Économie & Gestion, Maths, Sciences.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4900.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-logistique-production",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Logistique & Gestion de la Production",
        "description": "Gestion des approvisionnements, gestion des entrepôts, planification de production, Lean management et flux industriels.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Gestionnaire des stocks, Coordinateur logistique, Technicien de planification industrielle, Gestionnaire des approvisionnements.",
        "specialties": [{"code": "LOG-PROD", "name": "Logistique Industrielle & Flux de Production", "description": "Gestion des stocks, ordonnancement et Lean Manufacturing."}],
        "courses": [
            {"code": "LOG-101", "name": "Gestion des Stocks & Entreposage", "semester": "S1", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Modèles de réapprovisionnement, méthode ABC, inventaires."},
            {"code": "LOG-102", "name": "Planification & Ordonnancement de Production", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "PIC, PDP, calcul des besoins nets (CBN/MRP)."},
        ],
        "conditions": [{"title": "Baccalauréat toutes sections", "description": "Baccalauréat scientifique, technique ou économie.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4800.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement par tranches. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-marketing",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Marketing Digital & Communication",
        "description": "Comportement du consommateur, études de marché, stratégie de marque, gestion des réseaux sociaux, SEO/SEA et marketing de contenu.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Community Manager, Chargé de marketing digital, Chef de produit junior, Concepteur-rédacteur de contenu.",
        "specialties": [{"code": "MKT-DIGITAL", "name": "Marketing Digital & Stratégie Social Media", "description": "Campagnes publicitaires web, analytics, copywriting et image de marque."}],
        "courses": [
            {"code": "MKT-101", "name": "Marketing Fondamental & Études de Marché", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Segmentation, ciblage, positionnement et marketing mix (4P)."},
            {"code": "MKT-102", "name": "Outils du Marketing Digital & SEO", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Référencement naturel, Google Ads, analyse de trafic et conversion."},
        ],
        "conditions": [{"title": "Baccalauréat toutes sections", "description": "Baccalauréat toutes filières.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4800.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-ressources-humaines",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Gestion des Ressources Humaines",
        "description": "Recrutement, gestion des compétences, paie et administration du personnel, droit du travail, communication interne et bien-être en entreprise.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Chargé de recrutement, Gestionnaire de paie et administration RH, Assistant RH, Chargé de formation.",
        "specialties": [{"code": "RH-DEV", "name": "Développement des Compétences & Recrutement", "description": "GPEC, talent acquisition, évaluation et onboarding."}],
        "courses": [
            {"code": "RH-101", "name": "Gestion Administrative & Paie", "semester": "S1", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Contrats de travail, bulletins de paie, déclarations sociales."},
            {"code": "RH-102", "name": "Processus de Recrutement & Intégration", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Fiches de poste, sourcing, entretiens d'embauche, fidélisation."},
        ],
        "conditions": [{"title": "Baccalauréat toutes sections", "description": "Baccalauréat Économie, Lettres ou Sciences.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4600.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement par tranches. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-business-economics",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Business Economics (Track Anglais)",
        "description": "Approche rigoureuse combinant microéconomie d'entreprise, macroéconomie internationale, analyse conjoncturelle, politiques économiques et économétrie des marchés.",
        "duration_years": 3,
        "language": "en",
        "careers": "Economic Research Analyst, Market Strategist, Policy Advisor Assistant, Business Consultant.",
        "specialties": [{"code": "ECO-APPLIED", "name": "Applied Econometrics & Market Research", "description": "Statistical modeling of consumer and industry trends."}],
        "courses": [
            {"code": "ECO-101", "name": "Microeconomics & Industrial Economics", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Consumer theory, production costs, market structures and monopoly."},
            {"code": "ECO-102", "name": "Macroeconomics & Monetary Policy", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Inflation, GDP growth, central banking and exchange rate regimes."},
        ],
        "conditions": [{"title": "Baccalauréat avec bon niveau d'anglais", "description": "Baccalauréat Économie, Maths ou Sciences.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("5000.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-transport-logistique",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Transport International & Logistique",
        "description": "Techniques du commerce international : fret maritime, aérien et routier, procédures douanières, Incoterms, assurances transport et logistique portuaire.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Agent de transit maritime/aérien, Déclarant en douane, Coordinateur transport international, Exploitant logistique.",
        "specialties": [{"code": "TRANS-INT", "name": "Commerce Extérieur & Transit International", "description": "Incoterms 2020, chaîne logistique multimodale et formalités douanières."}],
        "courses": [
            {"code": "TRL-101", "name": "Techniques de Transport Multimodal & Fret", "semester": "S1", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Conteneurisation, affrètement, connaissement (Bill of Lading)."},
            {"code": "TRL-102", "name": "Réglementation Douanière & Incoterms", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Nomenclature douanière, dédouanement, crédits documentaires."},
        ],
        "conditions": [{"title": "Baccalauréat toutes sections", "description": "Baccalauréat toutes options.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4800.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement par tranches. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-droit-affaires",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Droit des Affaires & Fiscalité",
        "description": "Droit des sociétés, droit commercial, droit des contrats d'affaires, droit fiscal et propriété intellectuelle au service de l'entreprise moderne.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Juriste junior d'entreprise, Assistant juridique en cabinet d'avocats, Collaborateur conformité / compliance, Gestionnaire de contentieux.",
        "specialties": [{"code": "DROIT-AFFAIRES", "name": "Droit Commercial & Sociétés", "description": "Constitution de sociétés, pactes d'actionnaires, baux commerciaux."}],
        "courses": [
            {"code": "DA-101", "name": "Droit des Sociétés Commerciales", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "SARL, SA, SUARL, responsabilité des dirigeants et gouvernance."},
            {"code": "DA-102", "name": "Droit des Contrats d'Affaires", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Formation, exécution, rupture contractuelle, clauses pénales."},
        ],
        "conditions": [{"title": "Baccalauréat Lettres, Économie ou Sciences", "description": "Baccalauréat toutes filières, bonne aisance rédactionnelle.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4700.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement par tranches. Frais indicatifs."}],
    },
    {
        "slug": "isb-licence-droit-prive",
        "institution": Institution.ISB,
        "level": "licence",
        "name": "Licence en Droit Privé",
        "description": "Formation juridique fondamentale en droit civil, droit des obligations, droit des personnes et de la famille, droit pénal et procédure judiciaire.",
        "duration_years": 3,
        "language": "fr",
        "careers": "Préparation aux carrières judiciaires (avocature, magistrature, notariat), Conseil juridique, Collaborateur d'huissier de justice.",
        "specialties": [{"code": "DROIT-PRIV", "name": "Droit Civil & Contentieux Judiciaire", "description": "Procédure civile, voies d'exécution et responsabilité civile."},
        ],
        "courses": [
            {"code": "DP-101", "name": "Droit des Obligations & des Contrats", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Théorie générale des obligations, consentement, nullités."},
            {"code": "DP-102", "name": "Droit Pénal Général", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Éléments constitutifs de l'infraction, culpabilité et peines."},
        ],
        "conditions": [{"title": "Baccalauréat toutes sections", "description": "Baccalauréat Lettres, Économie ou Sciences.", "required_diploma": "Baccalauréat", "min_average": Decimal("10.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("4700.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },

    # --- 10 Mastères / MBA ISB ---
    {
        "slug": "isb-master-mba",
        "institution": Institution.ISB,
        "level": "master",
        "name": "International Master of Business Administration (MBA - Track Anglais)",
        "description": "Programme d'excellence executive dispensé en anglais : leadership stratégique, finance d'entreprise internationale, innovation technologique, gouvernance et négociation globale.",
        "duration_years": 2,
        "language": "en",
        "careers": "Executive Director, Chief Operations Officer, Management Consultant, International Project Director.",
        "specialties": [{"code": "MBA-EXEC", "name": "Executive Leadership & Strategy", "description": "Corporate transformation, competitive advantage and executive decision making."}],
        "courses": [
            {"code": "MBA-501", "name": "Global Strategic Management", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Industry dynamics, blue ocean strategy, corporate governance."},
            {"code": "MBA-502", "name": "Corporate Finance & Capital Markets", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Capital structure, M&A valuation, venture capital and risk management."},
        ],
        "conditions": [{"title": "Licence Bac+3 & Entretien d'admission", "description": "Licence en gestion, économie, ingénierie ou diplôme équivalent avec expérience ou motivation validée en entretien.", "required_diploma": "Licence Bac+3", "min_average": Decimal("11.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("7500.00"), "registration_fee": Decimal("500.00"), "currency": "TND", "payment_terms": "Paiement en 3 échéances (fourchette indicative 5000-8000 DT/an). Frais indicatifs."}],
    },
    {
        "slug": "isb-master-science-finance",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Master of Science in Finance & Investment Banking (Track Anglais)",
        "description": "Analyse financière avancée, ingénierie financière, gestion des risques de marché, valorisation de portefeuilles et technologies financières (Fintech).",
        "duration_years": 2,
        "language": "en",
        "careers": "Financial Analyst, Portfolio Manager, Risk Analyst, Investment Banking Associate.",
        "specialties": [{"code": "MS-FIN", "name": "Quantitative Finance & Fintech", "description": "Derivative pricing, algorithmic trading foundations and risk hedging."}],
        "courses": [
            {"code": "MSF-501", "name": "Financial Econometrics & Risk Modeling", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Value at Risk (VaR), time series analysis, portfolio optimization."},
            {"code": "MSF-502", "name": "Investment Valuation & Mergers", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "DCF models, multiples method, LBO structuring."},
        ],
        "conditions": [{"title": "Licence en Finance, Économie ou Gestion", "description": "Licence avec bagage quantitatif solide et entretien d'admission.", "required_diploma": "Licence Bac+3", "min_average": Decimal("11.50"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("7000.00"), "registration_fee": Decimal("500.00"), "currency": "TND", "payment_terms": "Paiement en 3 versements. Frais indicatifs."}],
    },
    {
        "slug": "isb-master-marketing-digital-en",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Master of Science in Digital Marketing & Growth Hacking (Track Anglais)",
        "description": "Techniques avancées de croissance digitale : growth hacking, attribution multi-touch, inbound marketing, analytics avancés et campagnes omnicanales.",
        "duration_years": 2,
        "language": "en",
        "careers": "Growth Hacker, Digital Strategist, Performance Marketing Manager, Chief Marketing Officer.",
        "specialties": [{"code": "MKT-GROWTH", "name": "Growth Hacking & Marketing Analytics", "description": "Funnel optimization, A/B testing at scale, programmatic advertising."}],
        "courses": [
            {"code": "MSM-501", "name": "Data-Driven Marketing & Conversion Optimization", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "CRO, Google Analytics 4, customer journey mapping."},
            {"code": "MSM-502", "name": "Digital Acquisition & Growth Tactics", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Viral loops, paid acquisition strategies, automation tools."},
        ],
        "conditions": [{"title": "Licence Bac+3 en Gestion, Communication ou Info", "description": "Bon niveau d'anglais et passion pour l'écosystème numérique.", "required_diploma": "Licence Bac+3", "min_average": Decimal("11.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("6800.00"), "registration_fee": Decimal("500.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-mastere-marketing-digital-fr",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Mastère Professionnel en Marketing Digital & E-Commerce",
        "description": "Stratégie de marque sur le web, gestion de plateformes e-commerce (Shopify, WooCommerce), marketing d'influence, CRM et relation client omnicanale.",
        "duration_years": 2,
        "language": "fr",
        "careers": "Responsable E-Commerce, Chef de Projet Marketing Digital, Brand Manager, Consultant CRM.",
        "specialties": [{"code": "MKT-ECOM", "name": "E-Commerce & Gestion Omnicanale", "description": "Logistique e-commerce, parcours d'achat et fidélisation client."}],
        "courses": [
            {"code": "MPM-501", "name": "Management de Plateformes E-Commerce", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Catalogue produits, paiements en ligne, logistique du dernier kilomètre."},
            {"code": "MPM-502", "name": "Stratégie de Contenu & Marketing d'Influence", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Brand storytelling, partenariats créateurs, gestion de l'e-réputation."},
        ],
        "conditions": [{"title": "Licence en Gestion, Marketing ou Communication", "description": "Dossier académique et entretien individuel.", "required_diploma": "Licence Bac+3", "min_average": Decimal("10.50"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("6200.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement en 3 versements. Frais indicatifs."}],
    },
    {
        "slug": "isb-mastere-comptabilite",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Mastère Professionnel en Comptabilité, Contrôle & Audit (CCA)",
        "description": "Préparation avancée aux métiers de l'expertise comptable, du commissariat aux comptes et de l'audit financier : normes IFRS consolidées, fiscalité approfondie et audit légal.",
        "duration_years": 2,
        "language": "fr",
        "careers": "Expert-comptable stagiaire, Auditeur financier senior, Chef comptable, Directeur administratif et financier (DAF).",
        "specialties": [{"code": "CCA-AUDIT", "name": "Audit Financier & Consolidation des Comptes", "description": "Comptes de groupes, fusions, normes internationales ISA."}],
        "courses": [
            {"code": "CCA-501", "name": "Consolidation des Comptes & Normes IFRS", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Périmètre de consolidation, écarts d'acquisition, élimination des opérations internes."},
            {"code": "CCA-502", "name": "Audit Légal & Commissariat aux Comptes", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Planification de mission d'audit, contrôle interne, sondages et rapports d'audit."},
        ],
        "conditions": [{"title": "Licence en Comptabilité ou Finance", "description": "Licence en sciences comptables ou équivalent avec bon niveau technique.", "required_diploma": "Licence Comptabilité", "min_average": Decimal("11.50"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("6300.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-mastere-finance-entreprise",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Mastère Professionnel en Finance d'Entreprise & Ingénierie Financière",
        "description": "Décisions financières stratégiques des entreprises : montages financiers complexes, levées de fonds, capital-investissement, restructurations de dettes et évaluation financière.",
        "duration_years": 2,
        "language": "fr",
        "careers": "Responsable M&A, Analyste Private Equity, Trésorier de groupe, Consultant en ingénierie financière.",
        "specialties": [{"code": "FIN-ING", "name": "Ingénierie Financière & M&A", "description": "Due diligence financière, valorisation d'actifs et financements structurés."}],
        "courses": [
            {"code": "FE-501", "name": "Évaluation d'Entreprise & Fusions-Acquisitions", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Méthodes patrimoniales, DCF, synergies et structuration juridique et fiscale."},
            {"code": "FE-502", "name": "Gestion de Trésorerie de Groupe & Risques", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Centralisation de trésorerie (cash pooling), dérivés de taux et de change."},
        ],
        "conditions": [{"title": "Licence en Finance ou Gestion", "description": "Dossier universitaire et entretien de motivation.", "required_diploma": "Licence Bac+3", "min_average": Decimal("11.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("6200.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement en 3 versements. Frais indicatifs."}],
    },
    {
        "slug": "isb-mastere-droit-affaires",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Mastère Professionnel en Droit des Affaires & Conformité (Compliance)",
        "description": "Conseil juridique d'entreprise de haut niveau, gouvernance des risques légaux, conformité anti-blanchiment, protection des données personnelles (RGPD) et contentieux économique.",
        "duration_years": 2,
        "language": "fr",
        "careers": "Juriste d'Affaires Senior, Compliance Officer, Délégué à la Protection des Données (DPO), Avocat d'affaires.",
        "specialties": [{"code": "JUR-COMPLIANCE", "name": "Conformité Réglementaire & Risques Juridiques", "description": "Cartographie des risques de non-conformité, déontologie et droit pénal des affaires."}],
        "courses": [
            {"code": "JUR-501", "name": "Conformité d'Entreprise & Lutte Anti-Blanchiment (LAB)", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Dispositifs KYC, obligations de vigilance, réglementation bancaire."},
            {"code": "JUR-502", "name": "Droit des Données Personnelles & Numérique", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Conformité RGPD, cyber-risques, contrats cloud et propriété intellectuelle."},
        ],
        "conditions": [{"title": "Licence en Droit ou Équivalent", "description": "Licence en droit privé, droit des affaires ou sciences juridiques.", "required_diploma": "Licence en Droit", "min_average": Decimal("11.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("6000.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-mastere-marketing-distribution",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Mastère Professionnel en Marketing, Vente & Grande Distribution",
        "description": "Management des réseaux de distribution, négociations commerciales grand compte (Key Account), category management, merchandising et trade marketing.",
        "duration_years": 2,
        "language": "fr",
        "careers": "Key Account Manager, Chef de secteur grande distribution, Responsable merchandising, Directeur régional des ventes.",
        "specialties": [{"code": "DISTRIB-CAT", "name": "Category Management & Négociation B2B", "description": "Accords commerciaux, optimisation d'assortiments et relations distributeurs."}],
        "courses": [
            {"code": "MD-501", "name": "Négociation Commerciale Grand Compte", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Techniques de négociation raisonnée, plans d'affaires conjoints (JBP)."},
            {"code": "MD-502", "name": "Category Management & Merchandising Stratégique", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Implantation des rayons, études shoppers, rentabilité au mètre linéaire."},
        ],
        "conditions": [{"title": "Licence en Gestion, Marketing ou Vente", "description": "Sélection sur dossier et entretien individuel.", "required_diploma": "Licence Bac+3", "min_average": Decimal("10.50"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("6000.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement par tranches. Frais indicatifs."}],
    },
    {
        "slug": "isb-mastere-management-agroalimentaire",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Mastère Professionnel en Management de la Filière Agroalimentaire",
        "description": "Spécificités managériales et économiques du secteur agroalimentaire : normes sanitaires et qualité (ISO 22000, IFS/BRC), valorisation des produits du terroir, traçabilité et export.",
        "duration_years": 2,
        "language": "fr",
        "careers": "Responsable Qualité Agroalimentaire, Chef de produit Food, Responsable Supply Chain Agro, Auditeur filières agro.",
        "specialties": [{"code": "AGRO-QUALITE", "name": "Qualité, Sécurité Sanitaire & Traçabilité", "description": "Normes HACCP, audits sécurité des aliments et gestion des alertes sanitaires."}],
        "courses": [
            {"code": "AGR-501", "name": "Sécurité Alimentaire & Normes Internationales", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Management de la sécurité des denrées alimentaires ISO 22000."},
            {"code": "AGR-502", "name": "Marketing des Produits Alimentaires & Export", "semester": "S2", "credits_ects": Decimal("4.0"), "coefficient": Decimal("1.50"), "hours_lectures": 21, "hours_tutorials": 21, "description": "Labels d'origine, circuits de distribution spécialisés et réglementations d'exportation."},
        ],
        "conditions": [{"title": "Licence en Biologie, Agronomie, Gestion ou Agroalimentaire", "description": "Ouvert aux profils scientifiques et gestionnaires.", "required_diploma": "Licence Bac+3", "min_average": Decimal("10.50"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("6000.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement échelonné. Frais indicatifs."}],
    },
    {
        "slug": "isb-mastere-audit-interne",
        "institution": Institution.ISB,
        "level": "master",
        "name": "Mastère Professionnel en Audit Interne & Contrôle de Gestion",
        "description": "Cartographie des risques opérationnels, contrôle de gestion stratégique, tableaux de bord de pilotage, audit des processus et conformité aux normes IIA.",
        "duration_years": 2,
        "language": "fr",
        "careers": "Auditeur interne, Contrôleur de gestion central, Risk Manager, Consultant en organisation et processus.",
        "specialties": [{"code": "AUDIT-RISK", "name": "Management des Risques & Cadre COSO", "description": "Évaluation du contrôle interne, matrice des risques et plans d'actions d'audit."}],
        "courses": [
            {"code": "AIC-501", "name": "Méthodologie de l'Audit Interne & Normes IIA", "semester": "S1", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Charte d'audit, lettre de mission, feuille de révélation et de problème (FRAP)."},
            {"code": "AIC-502", "name": "Contrôle de Gestion & Pilotage de la Performance", "semester": "S2", "credits_ects": Decimal("5.0"), "coefficient": Decimal("2.00"), "hours_lectures": 28, "hours_tutorials": 28, "description": "Balanced Scorecard, méthode ABC/ABM, pilotage des coûts et des marges."},
        ],
        "conditions": [{"title": "Licence en Gestion, Économie, Finance ou Comptabilité", "description": "Solide sens de la rigueur et esprit critique.", "required_diploma": "Licence Bac+3", "min_average": Decimal("11.00"), "position": 1}],
        "tariffs": [{"academic_year": "2026-2027", "amount": Decimal("6200.00"), "registration_fee": Decimal("400.00"), "currency": "TND", "payment_terms": "Paiement par tranches. Frais indicatifs."}],
    },
]


def seed_database(db: Session) -> dict:
    """Insère ou met à jour les données réelles de l'ensemble du socle technique (SA-14, SA-18)."""
    synced_programs = 0
    synced_conditions = 0
    synced_tariffs = 0
    synced_specialties = 0
    synced_courses = 0
    synced_rag_docs = 0

    sync_log = SyncLog(
        entity_type="catalog_demo_seed",
        status=SyncStatus.in_progress,
        records_synced=0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(sync_log)
    db.commit()

    try:
        # 1. Alimentation du catalogue académique complet (Formations, Spécialités, Matières, Conditions, Tarifs)
        for pdata in DEMO_PROGRAMS:
            conditions_data = pdata.get("conditions", [])
            tariffs_data = pdata.get("tariffs", [])
            specialties_data = pdata.get("specialties", [])
            courses_data = pdata.get("courses", [])

            existing = db.scalar(select(Program).where(Program.slug == pdata["slug"]))
            if existing:
                program = existing
                program.name = pdata["name"]
                program.description = pdata["description"]
                program.level = pdata["level"]
                program.duration_years = pdata["duration_years"]
                program.language = pdata["language"]
                program.careers = pdata["careers"]
                program.is_active = True
            else:
                program = Program(
                    slug=pdata["slug"],
                    institution=pdata["institution"],
                    level=pdata["level"],
                    name=pdata["name"],
                    description=pdata["description"],
                    duration_years=pdata["duration_years"],
                    language=pdata["language"],
                    careers=pdata["careers"],
                    is_active=True,
                )
                db.add(program)
                db.flush()
                synced_programs += 1

            # Spécialités (SA-12)
            spec_map = {}
            for sdata in specialties_data:
                spec_exists = db.scalar(
                    select(Specialty).where(
                        Specialty.program_id == program.id,
                        Specialty.code == sdata["code"]
                    )
                )
                if not spec_exists:
                    spec = Specialty(
                        program_id=program.id,
                        name=sdata["name"],
                        code=sdata["code"],
                        description=sdata["description"],
                        is_active=True,
                    )
                    db.add(spec)
                    db.flush()
                    spec_map[sdata["code"]] = spec
                    synced_specialties += 1
                else:
                    spec_map[sdata["code"]] = spec_exists

            # Matières enseignées / Courses (SA-12)
            for cdata in courses_data:
                course_exists = db.scalar(
                    select(Course).where(
                        Course.program_id == program.id,
                        Course.code == cdata["code"]
                    )
                )
                if not course_exists:
                    course = Course(
                        program_id=program.id,
                        code=cdata["code"],
                        name=cdata["name"],
                        semester=cdata["semester"],
                        credits_ects=cdata["credits_ects"],
                        coefficient=cdata["coefficient"],
                        hours_lectures=cdata["hours_lectures"],
                        hours_tutorials=cdata["hours_tutorials"],
                        description=cdata["description"]
                    )
                    db.add(course)
                    synced_courses += 1

            # Conditions d'admission (SA-12)
            for cdata in conditions_data:
                cond_exists = db.scalar(
                    select(AdmissionCondition).where(
                        AdmissionCondition.program_id == program.id,
                        AdmissionCondition.title == cdata["title"],
                    )
                )
                if not cond_exists:
                    cond = AdmissionCondition(
                        program_id=program.id,
                        title=cdata["title"],
                        description=cdata["description"],
                        required_diploma=cdata["required_diploma"],
                        min_average=cdata["min_average"],
                        position=cdata["position"],
                    )
                    db.add(cond)
                    synced_conditions += 1

            # Tarifs (SA-12)
            for tdata in tariffs_data:
                tariff_exists = db.scalar(
                    select(Tariff).where(
                        Tariff.program_id == program.id,
                        Tariff.academic_year == tdata["academic_year"],
                    )
                )
                if not tariff_exists:
                    tariff = Tariff(
                        program_id=program.id,
                        academic_year=tdata["academic_year"],
                        amount=tdata["amount"],
                        registration_fee=tdata["registration_fee"],
                        currency=tdata["currency"],
                        payment_terms=tdata["payment_terms"],
                    )
                    db.add(tariff)
                    synced_tariffs += 1

        db.commit()

        # 2. Utilisateurs avec rôles spécifiques (Responsables IIT/ISB, Entretien, Direction, Candidat)
        STAFF_USERS = [
            {
                "email": "resp.iit@smartcampus.tn",
                "full_name": "Dr. Khaled Trabelsi (Responsable Académique IIT)",
                "role": Role.responsable_academique_iit,
            },
            {
                "email": "resp.isb@smartcampus.tn",
                "full_name": "Dr. Samira Khemakhem (Responsable Académique ISB)",
                "role": Role.responsable_academique_isb,
            },
            {
                "email": "resp.entretien@smartcampus.tn",
                "full_name": "M. Ahmed Rekik (Responsable Entretiens)",
                "role": Role.responsable_entretien,
            },
            {
                "email": "direction@smartcampus.tn",
                "full_name": "Direction Générale (Supervision & Reporting)",
                "role": Role.direction,
            },
        ]
        for staff in STAFF_USERS:
            existing_staff = db.scalar(select(User).where(User.email == staff["email"]))
            if not existing_staff:
                new_staff = User(
                    email=staff["email"],
                    password_hash=hash_password("Password123!"),
                    full_name=staff["full_name"],
                    role=staff["role"],
                    is_active=True,
                )
                db.add(new_staff)
                logger.info(f"Compte staff créé : {staff['email']} ({staff['role'].value})")

        cand_email = "candidat.demo@smartcampus.tn"
        demo_candidate = db.scalar(select(User).where(User.email == cand_email))
        if not demo_candidate:
            demo_candidate = User(
                email=cand_email,
                password_hash=hash_password("Password123!"),
                full_name="Mohamed Ben Salem",
                role=Role.candidat,
                is_active=True,
            )
            db.add(demo_candidate)
            db.flush()

        profile_exists = db.scalar(select(AcademicProfile).where(AcademicProfile.user_id == demo_candidate.id))
        if not profile_exists:
            profile = AcademicProfile(
                user_id=demo_candidate.id,
                bac_section="Mathématiques",
                bac_year=2023,
                bac_average=Decimal("15.20"),
                highest_diploma="Licence en Informatique",
                graduation_institution="Faculté des Sciences de Sfax",
                graduation_year=2026,
                notes="Major de promotion, projet de fin d'études axé sur le développement backend sécurisé."
            )
            db.add(profile)

        # 3. Dossier de candidature démo, documents et versions (SA-13, SA-14)
        prog_info = db.scalar(select(Program).where(Program.slug == "iit-cycle-ingenieur-informatique"))
        if prog_info:
            app_exists = db.scalar(
                select(Application).where(
                    Application.user_id == demo_candidate.id,
                    Application.program_id == prog_info.id,
                    Application.academic_year == "2026-2027"
                )
            )
            if not app_exists:
                demo_app = Application(
                    user_id=demo_candidate.id,
                    program_id=prog_info.id,
                    academic_year="2026-2027",
                    status=ApplicationStatus.under_review,
                    notes="Candidature avec demande de bourse d'excellence."
                )
                db.add(demo_app)
                db.flush()

                demo_doc = Document(
                    application_id=demo_app.id,
                    user_id=demo_candidate.id,
                    document_type=DocumentType.diplome,
                    filename="diplome_licence_informatique.pdf",
                    file_path="/storage/documents/diplome_licence_informatique_v2.pdf",
                    mime_type="application/pdf",
                    file_size=245000,
                    current_version=2,
                    is_verified=True
                )
                db.add(demo_doc)
                db.flush()

                v1 = DocumentVersion(
                    document_id=demo_doc.id,
                    version_number=1,
                    file_path="/storage/documents/diplome_licence_informatique_v1.pdf",
                    file_size=240000,
                    change_summary="Attestation provisoire de réussite"
                )
                v2 = DocumentVersion(
                    document_id=demo_doc.id,
                    version_number=2,
                    file_path="/storage/documents/diplome_licence_informatique_v2.pdf",
                    file_size=245000,
                    change_summary="Diplôme définitif avec cachet officiel"
                )
                db.add_all([v1, v2])

                v_task = VectorSyncTask(
                    document_id=demo_doc.id,
                    action=VectorSyncAction.upsert,
                    status=VectorSyncStatus.completed,
                    embedding_model="text-embedding-3-small",
                    collection_name="smartcampus_documents",
                    chunk_count=6,
                    vector_dimensions=1536,
                    processed_at=datetime.now(timezone.utc)
                )
                db.add(v_task)

                interview_time = datetime.now(timezone.utc) - timedelta(days=2)
                interview = InterviewAppointment(
                    application_id=demo_app.id,
                    scheduled_at=interview_time,
                    duration_minutes=30,
                    location_or_link="https://meet.google.com/smartcampus-eval",
                    status=InterviewStatus.effectue,
                    notes="Entretien technique et d'admissibilité"
                )
                db.add(interview)
                db.flush()

                interview_res = InterviewResult(
                    interview_id=interview.id,
                    application_id=demo_app.id,
                    technical_score=Decimal("16.50"),
                    motivation_score=Decimal("17.00"),
                    language_score=Decimal("15.50"),
                    overall_score=Decimal("16.33"),
                    decision=JuryDecision.favorable,
                    jury_feedback="Excellent candidat, solides bases en algorithmique et motivation exemplaire pour le cycle ingénieur IIT."
                )
                db.add(interview_res)

                eq_req = EquivalenceRequest(
                    user_id=demo_candidate.id,
                    target_program_id=prog_info.id,
                    source_diploma="Licence Appliquée en Technologies de l'Information",
                    source_institution="Université Publique",
                    source_country="Tunisie",
                    requested_level="1ère année Cycle Ingénieur",
                    status=EquivalenceStatus.approved,
                    decision_notes="Équivalence validée par la commission pédagogique suite à l'examen du relevé de notes."
                )
                db.add(eq_req)

        # 4. Synchronisation des documents du Corpus RAG Officiel (SA-14)
        corpus_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "corpus_rag_iit_isb.json")
        if os.path.exists(corpus_path):
            with open(corpus_path, "r", encoding="utf-8") as f:
                rag_docs = json.load(f)

            for rdoc in rag_docs:
                doc_fname = f"{rdoc['document_id']}.json"
                existing_doc = db.scalar(select(Document).where(Document.filename == doc_fname))
                if not existing_doc:
                    is_verif = (rdoc.get("statut_verification") == "verifie")
                    content_str = rdoc.get("content", "")
                    new_doc = Document(
                        application_id=None,
                        user_id=None,
                        document_type=DocumentType.autre,
                        filename=doc_fname,
                        file_path=rdoc.get("source_url", ""),
                        mime_type="application/json",
                        file_size=len(content_str.encode("utf-8")),
                        current_version=1,
                        is_verified=is_verif
                    )
                    db.add(new_doc)
                    db.flush()

                    # Tâche vectorielle associée
                    v_task = VectorSyncTask(
                        document_id=new_doc.id,
                        action=VectorSyncAction.upsert,
                        status=VectorSyncStatus.completed,
                        embedding_model="text-embedding-3-small",
                        collection_name="smartcampus_rag_corpus",
                        chunk_count=max(1, len(content_str) // 300),
                        vector_dimensions=1536,
                        processed_at=datetime.now(timezone.utc)
                    )
                    db.add(v_task)
                    synced_rag_docs += 1

        db.commit()

        total_synced = synced_programs + synced_conditions + synced_tariffs + synced_specialties + synced_courses + synced_rag_docs
        sync_log.status = SyncStatus.success
        sync_log.records_synced = total_synced
        sync_log.completed_at = datetime.now(timezone.utc)
        db.commit()

        result = {
            "programs_created": synced_programs,
            "specialties_created": synced_specialties,
            "courses_created": synced_courses,
            "conditions_created": synced_conditions,
            "tariffs_created": synced_tariffs,
            "rag_docs_synced": synced_rag_docs,
            "total_records": total_synced,
            "demo_candidate": cand_email,
        }
        logger.info(f"Seeding officiel terminé avec succès : {result}")
        return result

    except Exception as exc:
        db.rollback()
        sync_log.status = SyncStatus.failed
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.error(f"Échec lors du seeding : {exc}")
        raise


if __name__ == "__main__":
    with SessionLocal() as session:
        seed_database(session)
