import logging
import os
import time
from dataclasses import dataclass

import pandas as pd
from google import genai
from google.genai import errors, types

from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE

API_KEY_VARIABLE = "GEMINI_API_KEY"
MODEL_VARIABLE = "GEMINI_MODEL"
DEFAULT_MODEL = "gemini-3.5-flash"
REQUEST_TIMEOUT_MILLISECONDS = 30000
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2
MISSING_KEY_REASON = f"a variável {API_KEY_VARIABLE} não está configurada"
EMPTY_RESPONSE_REASON = "o Gemini devolveu uma resposta vazia"
NOT_APPLICABLE = "não se aplica"
UNKNOWN_ACCOUNT = "conta não identificada"

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Aja como um vendedor B2B. Escreva um e-mail curto, direto e educado de follow-up para este deal. "
    "Se for um deal estagnado, o tom deve ser de retomada ou de encerramento amigável. "
    "Se for prospecção, o e-mail deve ser um convite para uma call. "
    "Não invente nomes de empresas nem de pessoas: se o contexto não trouxer, use [Nome da Empresa] "
    "e [Nome do Cliente]. O valor e a classificação interna do deal são contexto para você e não "
    "devem aparecer no e-mail. Assine com o nome do vendedor informado. Responda com a linha "
    "'Assunto:' seguida do corpo do e-mail, sem comentários extras."
)

SITUATION_BY_QUEUE = {
    WORK_NOW_QUEUE: "negociação ativa, dentro do ciclo típico de fechamento",
    REQUALIFY_QUEUE: "deal estagnado, aberto além do ciclo típico",
    QUALIFY_QUEUE: "prospecção, ainda sem contato avançado",
}

TEMPLATE_BY_QUEUE = {
    WORK_NOW_QUEUE: (
        "Assunto: Próximos passos sobre {product}\n\n"
        "Olá [Nome do Cliente],\n\n"
        "Retomo nossa conversa sobre {product} para alinharmos os próximos passos. "
        "Restou alguma dúvida técnica ou comercial que eu possa resolver esta semana?\n\n"
        "Atenciosamente,\n{seller}"
    ),
    REQUALIFY_QUEUE: (
        "Assunto: Ainda faz sentido avançarmos com {product}?\n\n"
        "Olá [Nome do Cliente],\n\n"
        "Nossa conversa sobre {product} está parada há {days} dias. Para não tomar seu tempo, "
        "gostaria de confirmar se o projeto continua nos planos da [Nome da Empresa] ou se "
        "podemos encerrar este assunto por ora.\n\n"
        "Atenciosamente,\n{seller}"
    ),
    QUALIFY_QUEUE: (
        "Assunto: Conversa rápida sobre {product}\n\n"
        "Olá [Nome do Cliente],\n\n"
        "Acredito que {product} pode ajudar a [Nome da Empresa]. "
        "Você teria 15 minutos na próxima semana para uma call?\n\n"
        "Atenciosamente,\n{seller}"
    ),
}


@dataclass
class EmailDraft:
    text: str
    usedAi: bool
    model: str
    fallbackReason: str = ""


def draftEmail(deal, writeWithAi=None):
    writeWithAi = writeWithAi or writeWithGemini
    if not os.environ.get(API_KEY_VARIABLE):
        return buildTemplateDraft(deal, MISSING_KEY_REASON)
    try:
        text = writeWithAi(buildPrompt(deal))
    except Exception as error:
        logger.warning("Falha ao chamar o Gemini: %s", error, exc_info=True)
        reason = f"falha ao chamar o Gemini com o modelo {modelName()} ({describeError(error)})"
        return buildTemplateDraft(deal, reason)
    if not text or not text.strip():
        return buildTemplateDraft(deal, EMPTY_RESPONSE_REASON)
    return EmailDraft(text=text.strip(), usedAi=True, model=modelName())


def modelName():
    return os.environ.get(MODEL_VARIABLE, DEFAULT_MODEL)


def describeError(error):
    if isinstance(error, errors.APIError):
        return f"{type(error).__name__} {error.code} {error.status}"
    return type(error).__name__


def retryOnServerError(call, attempts=MAX_ATTEMPTS, delaySeconds=RETRY_DELAY_SECONDS, sleep=time.sleep):
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except errors.ServerError:
            if attempt == attempts:
                raise
            sleep(delaySeconds * attempt)


def writeWithGemini(prompt):
    return retryOnServerError(lambda: requestGeminiText(prompt))


def requestGeminiText(prompt):
    client = genai.Client(
        api_key=os.environ[API_KEY_VARIABLE],
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MILLISECONDS),
    )
    response = client.models.generate_content(
        model=modelName(),
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
    )
    return response.text


def buildPrompt(deal):
    return "\n".join(
        [
            "Contexto do deal:",
            f"- Produto: {deal['product']}",
            f"- Valor (uso interno): {deal['sales_price']:.0f}",
            f"- Fila: {deal['queue']} ({SITUATION_BY_QUEUE[deal['queue']]})",
            f"- Dias em aberto: {describeDaysOpen(deal)}",
            f"- Conta: {describeAccount(deal)}",
            f"- Vendedor (assinatura): {deal['sales_agent']}",
        ]
    )


def describeDaysOpen(deal):
    return NOT_APPLICABLE if pd.isna(deal["age_days"]) else str(int(deal["age_days"]))


def describeAccount(deal):
    return UNKNOWN_ACCOUNT if pd.isna(deal["account"]) else deal["account"]


def buildTemplateDraft(deal, reason):
    text = TEMPLATE_BY_QUEUE[deal["queue"]].format(
        product=deal["product"],
        days=describeDaysOpen(deal),
        seller=deal["sales_agent"],
    )
    return EmailDraft(text=text, usedAi=False, model="", fallbackReason=reason)