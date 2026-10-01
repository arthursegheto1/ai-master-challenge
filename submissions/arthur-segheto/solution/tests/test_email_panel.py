from streamlit.testing.v1 import AppTest

from scoring.ai_writer import EmailDraft

EMAIL_TEXT = "Assunto: Olá\n\nCorpo do rascunho"


def panelScript():
    import pandas as pd

    from scoring.email_panel import renderEmailDrafter

    renderEmailDrafter(pd.Series({"opportunity_id": "ABC123"}))


def fakeDraftEmail(deal):
    return EmailDraft(text=EMAIL_TEXT, usedAi=True, model="modelo-de-teste")


def startPanel(monkeypatch):
    monkeypatch.setattr("scoring.email_panel.draftEmail", fakeDraftEmail)
    return AppTest.from_function(panelScript).run()


def testPanelShowsOnlyTheButtonBeforeTheClick(monkeypatch):
    panel = startPanel(monkeypatch)
    assert len(panel.button) == 1
    assert len(panel.text_area) == 0


def testClickShowsTheDraftInAnEditableTextArea(monkeypatch):
    panel = startPanel(monkeypatch)
    panel.button[0].click().run()
    assert panel.text_area[0].value == EMAIL_TEXT


def testEditedDraftSurvivesTheRerunTriggeredByTyping(monkeypatch):
    panel = startPanel(monkeypatch)
    panel.button[0].click().run()
    panel.text_area[0].set_value("Texto editado pelo vendedor").run()
    assert panel.text_area[0].value == "Texto editado pelo vendedor"


def testDraftWithoutAiShowsAWarning(monkeypatch):
    noAiDraft = EmailDraft(text=EMAIL_TEXT, usedAi=False, model="", fallbackReason="sem chave")
    monkeypatch.setattr("scoring.email_panel.draftEmail", lambda deal: noAiDraft)
    panel = AppTest.from_function(panelScript).run()
    panel.button[0].click().run()
    assert "sem chave" in panel.warning[0].value
