# Ylohann

Réseau social privé construit avec Flask, PostgreSQL, HTML, CSS et JavaScript.

La connexion accepte le nom d’utilisateur, l’email ou le numéro de téléphone, avec mot de passe individuel et option « Se souvenir de moi ». Une connexion Facebook demanderait une configuration OAuth séparée.

Le profil peut être modifié avec changement de nom d’utilisateur, biographie et avatar. Les membres peuvent publier, liker, commenter, inviter leurs amis, échanger des messages privés et partager le lien Ylohann.

Les paramètres permettent aussi de modifier l’email, le téléphone associé et le mot de passe après vérification de l’ancien mot de passe. Le thème sombre est activé par défaut et le logo Ylohann est intégré en CSS.

## Lancer en local

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "une-cle-secrete-locale"
$env:INVITATION_CODE = "Ylianna"
py app.py
```

Puis ouvrir `http://127.0.0.1:5000`.

## Déployer

Le fichier `render.yaml` configure un service web Render avec une base PostgreSQL. Définir une vraie valeur aléatoire pour `SECRET_KEY` et, idéalement, remplacer le code d’invitation par une valeur secrète dans les variables d’environnement.

Pour une mise en production complète, ajouter ensuite une protection CSRF, une limitation de tentatives de connexion et une modération avant ouverture publique.
