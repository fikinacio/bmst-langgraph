# Knowledge Base — Marché Suisse Romande: Tarifs, Segments et Conformité

## Contexte du Marché

### Pourquoi la Suisse Romande?
- Marché mature avec budget IT établi
- Forte concentration de fiduciaires, PME industrielles et cabinets médicaux
- Moins saturé que Zürich sur le segment IA/automatisation francophone
- Décideurs accessibles (taille des entreprises: 10–200 employés)
- Exigence de qualité élevée → justifie les tarifs premium

### Comportement d'Achat Suisse (vs Angola)
| Critère | Suisse | Angola |
|---|---|---|
| Canal de contact | Email + LinkedIn | WhatsApp |
| Cycle de vente | 3–8 semaines | 1–3 semaines |
| Décision | Rationnelle, chiffres | Relationnelle, confiance |
| Paiement | Ponctuel (30 jours) | Souvent en retard |
| Langue | Français professionnel | Português informal |
| Contrat | Obligatoire, signé | Souvent verbal |

---

## Grille Tarifaire — Fidel Kussunga (Suisse)

### Taux de Base (2026)
| Prestation | Tarif bas (CHF) | Tarif haut (CHF) | Unité |
|---|---|---|---|
| Taux journalier (TJM) | 950 | 1'400 | / jour |
| Taux horaire (missions courtes) | 130 | 200 | / heure |
| Atelier découverte IA (½ j.) | 800 | 1'500 | forfait |
| Audit processus + recommandations | 2'500 | 6'000 | forfait |
| Projet pilote IA (PoC) | 5'000 | 15'000 | forfait |
| Automatisation processus | 8'000 | 25'000 | forfait |
| Chatbot / assistant IA | 6'000 | 20'000 | forfait |
| Agent IA sur mesure | 10'000 | 35'000 | forfait |
| Retainer mensuel | 1'500 | 4'000 | / mois |
| Formation équipe IA (½–1 j.) | 1'200 | 3'000 | forfait |

### Positionnement Recommandé (Entrée de Marché)
- **TJM de départ:** CHF 950/jour — compétitif sans brader
- **Objectif à 6 mois:** CHF 1'200/jour après premières références
- **Projet minimum:** CHF 3'000 — en dessous, pas rentable
- **Première mission recommandée:** Atelier découverte (CHF 800–1'500) ou audit (CHF 2'500) → porte d'entrée vers projet complet

### Conditions de Paiement (Suisse)
- Délai standard: 30 jours net
- Pour projets > CHF 8'000: 30% à la signature, 40% mi-projet, 30% à la livraison
- Pour projets < CHF 8'000: 50% à la signature, 50% à la livraison
- Facturation en CHF exclusivement

---

## Segments Cibles — Suisse Romande

### Priorité 1 — Fiduciaires et Cabinets Comptables
**Pourquoi:** Tâches répétitives massives (saisie, rapprochements, rapports). Budget IT existant. Décision rapide si ROI clair.
**Pain points:** Saisie manuelle de données, génération de rapports, communication client répétitive
**Solution BMST:** Automatisation de saisie + assistant IA pour communication client + génération de rapports
**Interlocuteur:** Associé gérant ou directeur de cabinet
**Associations:** TREUHAND|SUISSE (fiduciaires), EXPERTsuisse (experts-comptables)

### Priorité 2 — PME Industrielles et de Services (10–100 employés)
**Pourquoi:** Processus souvent non-digitalisés, marge pour automatisation. Budget tech croissant.
**Pain points:** Gestion des commandes manuelle, suivi client, rapports de production
**Solution BMST:** Automatisation workflows + intégration systèmes
**Interlocuteur:** Directeur général ou directeur opérationnel

### Priorité 3 — Cabinets Médicaux, Dentaires et Thérapeutiques
**Pourquoi:** Volume de RDV et administratif élevé. Secret médical = différenciateur (solutions self-hosted)
**Pain points:** Gestion RDV, rappels patients, documentation
**Solution BMST:** Assistant IA conforme secret médical + automatisation administrative
**Interlocuteur:** Médecin propriétaire ou manager de cabinet

### Priorité 4 — Agences Immobilières
**Pourquoi:** Fort volume de contacts entrants. Qualification de prospects chronophage.
**Pain points:** Réponse aux demandes de renseignements, qualification de locataires/acheteurs
**Solution BMST:** Chatbot qualification leads + automatisation suivi (expérience directe avec client à Lausanne)
**Interlocuteur:** Directeur ou propriétaire de l'agence

### Priorité 5 — Startups en Croissance (Vaud/Genève)
**Pourquoi:** Ouvertes à l'IA, budget VC, besoin d'architecture dès le départ
**Pain points:** Scalabilité, onboarding clients, support automatisé
**Solution BMST:** Architecture IA complète dès le départ

---

## Conformité LPD/RGPD — Points Essentiels

### LPD (Loi fédérale sur la Protection des Données)
- En vigueur depuis septembre 2023
- Applicable à toute personne physique ou morale traitant des données de résidents suisses
- **Privacy by design obligatoire:** minimisation des données, chiffrement, accès restreint

### Obligations pratiques pour Fidel
1. **Mentions légales** dans chaque email de prospection + opt-out fonctionnel
2. **Contrat de traitement des données** à signer avec chaque client (si accès aux données de leurs clients)
3. **Hébergement en Suisse ou UE** — VPS Hostinger (EU) acceptable si données chiffrées
4. **Pas de transfert vers pays tiers** sans consentement explicite (pas de logs en dehors EU/CH)
5. **Registre des traitements** — documenter quelles données sont traitées, pourquoi, combien de temps

### Argument commercial LPD (avantage concurrentiel)
> "Contrairement aux solutions cloud américaines, notre implémentation self-hosted garantit que les données de vos clients restent sur des serveurs en Europe, sous votre contrôle total."

### Conformité des outils utilisés
| Outil | Hébergement | LPD OK? |
|---|---|---|
| n8n self-hosted | VPS EU | ✅ |
| Dify self-hosted | VPS EU | ✅ |
| Supabase | EU region | ✅ |
| DocuSeal self-hosted | VPS EU | ✅ |
| HubSpot | US servers | ⚠️ Données de contact uniquement, pas de données clients finaux |
| Claude API (Anthropic) | US | ⚠️ Ne pas envoyer de données personnelles de clients finaux |
