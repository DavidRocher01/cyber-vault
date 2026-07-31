"""
Tests unitaires — app/services/newsletter_email.py

Ce module etait le seul VRAI angle mort revele par la remise sous mesure de la
couverture le 2026-07-30 : 25 % couvert, cite dans aucun test, alors qu'il
construit du HTML a partir d'entrees externes (titres d'articles, URLs de
desabonnement) et l'envoie a des abonnes.

L'essentiel des tests ci-dessous porte donc sur les DEUX gardes de securite du
module — l'echappement HTML et le filtrage des schemas d'URL — parce qu'un
`javascript:` ou un `<script>` qui passe finit dans la boite mail de quelqu'un.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import newsletter_email as ne

# ── _safe_url : garde anti-injection de schema ────────────────────────────────


class TestSafeUrl:
    """`_safe_url` doit neutraliser tout ce qui n'est pas http(s)."""

    @pytest.mark.parametrize(
        "hostile",
        [
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "data:text/html;base64,PHNjcmlwdD4=",
            "vbscript:msgbox(1)",
            "file:///etc/passwd",
            "//evil.example.com",
            "/chemin/relatif",
            "",
            "   ",
        ],
    )
    def test_schema_non_http_neutralise(self, hostile):
        assert ne._safe_url(hostile) == "#", f"{hostile!r} aurait du etre neutralise"

    def test_https_accepte(self):
        assert ne._safe_url("https://rochercybersecurite.com/x") == (
            "https://rochercybersecurite.com/x"
        )

    def test_http_accepte(self):
        assert ne._safe_url("http://example.com") == "http://example.com"

    def test_espaces_ignores_avant_validation(self):
        assert ne._safe_url("  https://example.com  ") == "https://example.com"

    def test_url_acceptee_est_aussi_echappee(self):
        """Une URL http valide contenant des guillemets ne doit pas casser
        l'attribut HTML dans lequel elle est interpolee."""
        out = ne._safe_url('https://example.com/?a="onload="alert(1)')
        assert '"' not in out
        assert "&quot;" in out


# ── _e : echappement HTML ─────────────────────────────────────────────────────


class TestEchappement:
    def test_balises_echappees(self):
        assert ne._e("<script>alert(1)</script>") == ("&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_guillemets_echappes(self):
        # quote=True : indispensable, le resultat est interpole dans des attributs.
        assert '"' not in ne._e('a "b" c')

    def test_esperluette_echappee(self):
        assert ne._e("a & b") == "a &amp; b"

    def test_non_chaine_accepte(self):
        assert ne._e(42) == "42"


# ── _send : les deux voies d'envoi ────────────────────────────────────────────


class TestSend:
    def test_utilise_resend_quand_la_cle_est_presente(self):
        envoi = MagicMock()
        with (
            patch.object(ne.settings, "RESEND_API_KEY", "re_test"),
            patch.object(ne.settings, "RESEND_FROM", "contact@test.fr"),
            patch.object(ne.resend.Emails, "send", envoi),
        ):
            ne._send("dest@test.fr", "Sujet", "<p>html</p>", "plain")

        assert envoi.called
        charge = envoi.call_args[0][0]
        assert charge["to"] == ["dest@test.fr"]
        assert charge["subject"] == "Sujet"
        assert charge["html"] == "<p>html</p>"
        assert charge["text"] == "plain"

    def test_repli_smtp_quand_la_cle_est_absente(self):
        serveur = MagicMock()
        with (
            patch.object(ne.settings, "RESEND_API_KEY", ""),
            patch.object(ne.smtplib, "SMTP_SSL") as smtp,
        ):
            smtp.return_value.__enter__.return_value = serveur
            ne._send("dest@test.fr", "Sujet", "<p>html</p>", "plain")

        assert serveur.login.called
        assert serveur.sendmail.called
        _, destinataire, corps = serveur.sendmail.call_args[0]
        assert destinataire == "dest@test.fr"
        assert "Sujet" in corps


# ── Les 5 emails publics : aucune entree hostile ne doit ressortir brute ──────


_XSS = '<script>alert("xss")</script>'
_URL_HOSTILE = "javascript:alert(1)"


def _capture():
    """Patch `_send` et rend le mock, pour inspecter le HTML reellement envoye."""
    return patch.object(ne, "_send")


class TestEmailsPublics:
    def test_confirmation_neutralise_une_url_hostile(self):
        with _capture() as envoi:
            ne.send_confirmation_email("a@test.fr", _URL_HOSTILE)
        html = envoi.call_args[0][2]
        assert "javascript:" not in html

    def test_confirmation_contient_bien_une_url_legitime(self):
        with _capture() as envoi:
            ne.send_confirmation_email("a@test.fr", "https://ok.test/confirm?t=1")
        html = envoi.call_args[0][2]
        assert "https://ok.test/confirm" in html

    def test_bienvenue_neutralise_url_desabonnement_hostile(self):
        with _capture() as envoi:
            ne.send_newsletter_welcome("a@test.fr", _URL_HOSTILE)
        assert "javascript:" not in envoi.call_args[0][2]

    def test_desabonnement_envoie_au_bon_destinataire(self):
        with _capture() as envoi:
            ne.send_unsubscribe_confirmation("a@test.fr")
        assert envoi.call_args[0][0] == "a@test.fr"

    def test_articles_echappent_les_titres(self):
        """Un titre d'article est une donnee externe : il doit etre echappe."""
        with _capture() as envoi:
            ne.send_newsletter_articles(
                "a@test.fr",
                "https://ok.test/unsub",
                7,
                [
                    {
                        "actu_title": _XSS,
                        "actu_url": _URL_HOSTILE,
                        "actu_source": _XSS,
                        "reflex": _XSS,
                    }
                ],
            )
        html = envoi.call_args[0][2]
        assert "<script>" not in html, "un titre d'article s'est retrouve brut dans le HTML"
        assert "javascript:" not in html
        assert "&lt;script&gt;" in html

    def test_articles_numero_edition_sur_trois_chiffres(self):
        with _capture() as envoi:
            ne.send_newsletter_articles("a@test.fr", "https://ok.test/u", 7, [])
        assert "007" in envoi.call_args[0][2]

    def test_issue_echappe_tous_les_blocs(self):
        with _capture() as envoi:
            ne.send_newsletter_issue(
                "a@test.fr",
                "https://ok.test/unsub",
                12,
                _XSS,
                _XSS,
                _XSS,
                _XSS,
                _XSS,
                _XSS,
            )
        html = envoi.call_args[0][2]
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_issue_numero_edition_sur_trois_chiffres(self):
        with _capture() as envoi:
            ne.send_newsletter_issue(
                "a@test.fr", "https://ok.test/u", 12, "a", "b", "c", "d", "e", "f"
            )
        assert "012" in envoi.call_args[0][2]

    @pytest.mark.parametrize(
        "fonction,args",
        [
            (ne.send_confirmation_email, ("a@test.fr", "https://ok.test/c")),
            (ne.send_newsletter_welcome, ("a@test.fr", "https://ok.test/u")),
            (ne.send_unsubscribe_confirmation, ("a@test.fr",)),
        ],
    )
    def test_version_texte_toujours_fournie(self, fonction, args):
        """Un email sans alternative texte part en spam plus facilement."""
        with _capture() as envoi:
            fonction(*args)
        plain = envoi.call_args[0][3]
        assert plain and plain.strip(), "version texte vide"
