from .conftest import ADMIN, H


def test_full_flow(c):
    assert c.get("/health").json() == {"status": "ok"}

    # visiteur : session + conversation anonyme
    assert c.post("/conversations", json={}).status_code == 401
    sess = c.post("/sessions").json()["session_token"]
    conv = c.post("/conversations", json={"title": "Prépa ou Licence ?"}, headers=H(session=sess)).json()
    assert conv["user_id"] is None

    # catalogue public vide, admin crée
    assert c.get("/programs").json() == []
    adm = c.post("/auth/login", json=ADMIN).json()["access_token"]
    p = {"slug": "licence-informatique", "institution": "IIT", "level": "Licence", "name": "Licence en Informatique",
         "duration_years": 3, "careers": "Développeur, data analyst"}
    assert c.post("/programs", json=p).status_code == 401
    assert c.post("/programs", json=p, headers=H(adm)).status_code == 201
    assert c.post("/programs", json=p, headers=H(adm)).status_code == 409
    assert c.post("/programs/licence-informatique/admission-conditions", headers=H(adm),
                  json={"title": "Baccalauréat", "required_diploma": "Bac", "min_average": 10}).status_code == 201
    assert c.post("/programs/licence-informatique/tariffs", headers=H(adm),
                  json={"academic_year": "2026-2027", "amount": 4500, "registration_fee": 200}).status_code == 201

    d = c.get("/programs/licence-informatique").json()
    assert len(d["conditions"]) == 1 and d["tariffs"][0]["academic_year"] == "2026-2027"
    assert len(c.get("/programs", params={"institution": "IIT", "level": "licence"}).json()) == 1
    assert c.get("/programs/licence-informatique/tariffs", params={"academic_year": "2025-2026"}).json() == []

    # candidat : inscription avec session → rattachement SA-29
    r = c.post("/auth/register", json={"email": "Med@Test.tn", "password": "motdepasse1", "full_name": "Med"},
               headers=H(session=sess))
    assert r.status_code == 201 and r.json()["linked_conversations"] == 1
    cand = r.json()["access_token"]
    assert c.get(f"/conversations/{conv['id']}", headers=H(cand)).json()["user_id"] == r.json()["user"]["id"]
    assert c.get("/auth/me", headers=H(cand)).json()["role"] == "candidat"

    # rôles
    assert c.post("/programs", json={**p, "slug": "x"}, headers=H(cand)).status_code == 403
    assert c.get("/admin/users", headers=H(cand)).status_code == 403
    assert len(c.get("/admin/users", headers=H(adm)).json()) == 2

    # désactivation logique
    assert c.delete("/programs/licence-informatique", headers=H(adm)).status_code == 204
    assert c.get("/programs/licence-informatique").status_code == 404
    assert c.get("/programs", params={"include_inactive": True}).status_code == 403
    assert len(c.get("/programs", params={"include_inactive": True}, headers=H(adm)).json()) == 1

    # mauvais mot de passe / jeton invalide
    assert c.post("/auth/login", json={"email": "med@test.tn", "password": "faux"}).status_code == 401
    assert c.get("/sessions/me", headers=H(session="bidon")).status_code == 401
