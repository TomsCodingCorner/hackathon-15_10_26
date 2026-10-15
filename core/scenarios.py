"""Handmatige scenario's; input bevat geen fictieve minorrecords."""

SCENARIOS = {
    "ICT en ondernemerschap": {
        "message": "Ik studeer HBO-ICT en wil leren ondernemen. Ik heb geen locatievoorkeur.",
        "expected": "Adviseer inhoudelijk passende bestaande minoren als de dataset die bevat; anders eerlijk doorverwijzen.",
    },
    "Zorg en psychologie": {
        "message": "Ik studeer verpleegkunde en wil mij verdiepen in psychologie.",
        "expected": "Gebruik zorgachtergrond en interesse, onderbouw met bronbeschrijving; geen toelating aannemen.",
    },
    "Nog geen voorkeur": {
        "message": "Ik weet nog niet welke minor ik wil en heb nog geen duidelijke interesse.",
        "expected": "Stel een gerichte verkennende vraag bij beschikbare data; voorkom eindeloos doorvragen.",
    },
    "Geen passende minor": {
        "message": "Ik wil uitsluitend een minor over de archeologie van onderwatersteden.",
        "expected": "Beoordeel werkelijk aanbod; geef geen geforceerde match en verwijs zo nodig naar een studieadviseur.",
    },
}
