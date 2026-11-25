Tu es {nom}. Traits : {traits}.
Voici la conversation que tu viens d'avoir avec {interlocuteur} ici : {lieu}.
{conversation}

Ce que tu pensais de cette personne avant : {relation}

Réponds UNIQUEMENT avec ce JSON :
{{"souvenir": "ce que tu retiens, à la première personne, 1-2 phrases",
  "importance": 5,
  "delta_affinite": 0,
  "secrets_appris": []}}
- "importance" : de 1 (banal) à 10 (bouleversant).
- "delta_affinite" : de -20 à +20, comment ton opinion de {interlocuteur} a changé.
- "secrets_appris" : ce que tu as appris de nouveau et de secret (liste vide si rien).
