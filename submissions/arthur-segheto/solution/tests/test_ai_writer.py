import pandas as pd
import pytest
from google.genai import errors

from scoring.ai_writer import (
    API_KEY_VARIABLE,
    DEFAULT_MODEL,
    UNKNOWN_ACCOUNT,
    buildPrompt,
    describeError,
    draftEmail,
    modelName,
    retryOnServerError,
)
from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE


def buildDeal(queue=WORK_NOW_QUEUE, ageDays=60.0, account="Acme Corp"):
    return pd.Series(
        {
            "product": "GTX Pro",
            "sales_price": 4821.0,
            "queue": queue,
            "age_days": ageDays,
            "account": account,
            "sales_agent": "Maria Souza",
        }
    )


def fakeWriter(prompt):
    return "Assunto: Teste\n\nCorpo do e-mail"


def failingWriter(prompt):
    raise RuntimeError("sem rede")


def buildServerError():
    return errors.ServerError(503, {"error": {"code": 503, "message": "overloaded", "status": "UNAVAILABLE"}})


def buildClientError():
    return errors.ClientError(400, {"error": {"code": 400, "message": "bad key", "status": "INVALID_ARGUMENT"}})


class FlakyCall:
    def __init__(self, failures, error):
        self.failures = failures
        self.error = error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return "texto"


@pytest.fixture
def withApiKey(monkeypatch):
    monkeypatch.setenv(API_KEY_VARIABLE, "chave-de-teste")


@pytest.fixture
def withoutApiKey(monkeypatch):
    monkeypatch.delenv(API_KEY_VARIABLE, raising=False)


def testPromptCarriesProductValueQueueAndDaysOpen():
    prompt = buildPrompt(buildDeal(queue=REQUALIFY_QUEUE, ageDays=200.0))
    assert "GTX Pro" in prompt
    assert "4821" in prompt
    assert REQUALIFY_QUEUE in prompt
    assert "200" in prompt


def testPromptDoesNotInventAnAccountWhenThereIsNone():
    prompt = buildPrompt(buildDeal(account=float("nan")))
    assert UNKNOWN_ACCOUNT in prompt


def testPromptSaysThatProspectingHasNoDaysOpen():
    prompt = buildPrompt(buildDeal(queue=QUALIFY_QUEUE, ageDays=float("nan")))
    assert "Dias em aberto: não se aplica" in prompt


def testPromptNamesTheSalesAgentForTheSignature():
    assert "Maria Souza" in buildPrompt(buildDeal())


def testDraftComesFromTheAiWhenAKeyIsConfigured(withApiKey):
    draft = draftEmail(buildDeal(), writeWithAi=fakeWriter)
    assert draft.usedAi
    assert "Corpo do e-mail" in draft.text


def testDraftFallsBackToTheTemplateWithoutAKey(withoutApiKey):
    draft = draftEmail(buildDeal(), writeWithAi=fakeWriter)
    assert not draft.usedAi
    assert "GEMINI_API_KEY" in draft.fallbackReason


def testDraftReportsTheFailureInsteadOfHidingIt(withApiKey):
    draft = draftEmail(buildDeal(), writeWithAi=failingWriter)
    assert not draft.usedAi
    assert "RuntimeError" in draft.fallbackReason


def testEmptyAiResponseFallsBackToTheTemplate(withApiKey):
    draft = draftEmail(buildDeal(), writeWithAi=lambda prompt: "  ")
    assert not draft.usedAi
    assert draft.fallbackReason


@pytest.mark.parametrize("queue", [WORK_NOW_QUEUE, REQUALIFY_QUEUE, QUALIFY_QUEUE])
def testTemplateIsSignedByTheSalesAgentAndHasNoLeftoverPlaceholders(withoutApiKey, queue):
    ageDays = float("nan") if queue == QUALIFY_QUEUE else 120.0
    text = draftEmail(buildDeal(queue=queue, ageDays=ageDays)).text
    assert "Maria Souza" in text
    assert "{" not in text


def testDraftReportsTheHttpStatusOfApiFailures(withApiKey):
    def serverFailure(prompt):
        raise buildServerError()

    draft = draftEmail(buildDeal(), writeWithAi=serverFailure)
    assert "ServerError 503 UNAVAILABLE" in draft.fallbackReason


def testDescribeErrorUsesTheTypeNameForPlainErrors():
    assert describeError(RuntimeError("x")) == "RuntimeError"


def testRetryRecoversFromATransientServerError():
    call = FlakyCall(failures=1, error=buildServerError())
    waits = []
    assert retryOnServerError(call, attempts=3, delaySeconds=2, sleep=waits.append) == "texto"
    assert waits == [2]


def testRetryGivesUpAfterTheLastAttempt():
    call = FlakyCall(failures=5, error=buildServerError())
    waits = []
    with pytest.raises(errors.ServerError):
        retryOnServerError(call, attempts=3, delaySeconds=1, sleep=waits.append)
    assert call.calls == 3
    assert len(waits) == 2


def testRetryDoesNotRepeatClientErrors():
    call = FlakyCall(failures=5, error=buildClientError())
    with pytest.raises(errors.ClientError):
        retryOnServerError(call, attempts=3, delaySeconds=1, sleep=lambda seconds: None)
    assert call.calls == 1


def testFailureReasonNamesTheModelThatWasCalled(withApiKey, monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "modelo-inexistente")
    draft = draftEmail(buildDeal(), writeWithAi=failingWriter)
    assert "modelo-inexistente" in draft.fallbackReason


def testModelFallsBackToTheDefaultWhenNoVariableIsSet(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert modelName() == DEFAULT_MODEL