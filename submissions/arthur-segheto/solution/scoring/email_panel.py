import streamlit as st

from scoring.ai_writer import draftEmail

EMAIL_BUTTON_LABEL = "Rascunhar e-mail com IA (Gemini)"
SPINNER_MESSAGE = "Gerando rascunho..."
EMAIL_BOX_HEIGHT = 280


def renderEmailDrafter(deal):
    dealId = deal["opportunity_id"]
    draftKey = f"email-draft-{dealId}"
    textKey = f"email-text-{dealId}"
    if st.button(EMAIL_BUTTON_LABEL, key=f"email-button-{dealId}"):
        with st.spinner(SPINNER_MESSAGE):
            draft = draftEmail(deal)
        st.session_state[draftKey] = draft
        st.session_state[textKey] = draft.text
    if draftKey in st.session_state:
        renderDraftSource(st.session_state[draftKey])
        st.text_area("Rascunho (editável, copie daqui)", key=textKey, height=EMAIL_BOX_HEIGHT)


def renderDraftSource(draft):
    if draft.usedAi:
        st.caption(f"Gerado por IA ({draft.model}). Revise antes de enviar.")
    else:
        st.warning(f"Modelo padrão, sem IA: {draft.fallbackReason}.")
